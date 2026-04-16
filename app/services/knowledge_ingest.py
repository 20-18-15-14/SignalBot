from pathlib import Path

from app.services.embeddings import EmbeddingAdapter
from app.services.repositories import Repository


class KnowledgeIngestService:
    def __init__(self, repository: Repository, embeddings: EmbeddingAdapter, chunk_max_chars: int = 2000):
        self.repository = repository
        self.embeddings = embeddings
        self.chunk_max_chars = max(500, chunk_max_chars)

    def ingest_file(
        self,
        path: Path,
        collection_scope: str,
        classification_label: str | None = None,
        group_id: str | None = None,
    ) -> int:
        suffix = path.suffix.lower()
        if suffix not in {".txt", ".md", ".pdf"}:
            raise ValueError(f"unsupported file type: {suffix}")

        if suffix == ".pdf":
            try:
                from pypdf import PdfReader
            except ImportError as exc:  # pragma: no cover - dependency missing
                raise ValueError("pypdf is required for PDF ingestion") from exc
            reader = PdfReader(str(path))
            pages = []
            for idx, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                pages.append((idx + 1, text.strip()))
            content = "\n\n".join(text for _, text in pages if text)
            source_type = "pdf"
        else:
            content = path.read_text(encoding="utf-8")
            source_type = suffix.lstrip(".")

        doc = self.repository.add_knowledge_document(
            file_name=path.name,
            source_type=source_type,
            classification_label=classification_label,
            collection_scope=collection_scope,
            content=content,
            metadata_json={"path": str(path), "collection_scope": collection_scope},
            group_id=group_id,
        )
        chunks = self._chunk_text(content)
        if not chunks:
            chunks = [content]
        for idx, paragraph in enumerate(chunks):
            embedding = self.embeddings.embed_text(paragraph)
            self.repository.add_knowledge_chunk(
                document_id=doc.id,
                collection_scope=collection_scope,
                content=paragraph,
                metadata_json={"chunk_index": idx, "file_name": path.name},
                embedding=embedding,
                group_id=group_id,
            )
        return len(chunks)

    def _chunk_text(self, content: str) -> list[str]:
        paragraphs = [part.strip() for part in content.split("\n\n") if part.strip()]
        if not paragraphs:
            return []
        chunks: list[str] = []
        buffer: list[str] = []
        length = 0
        for paragraph in paragraphs:
            if len(paragraph) > self.chunk_max_chars:
                if buffer:
                    chunks.append("\n\n".join(buffer))
                    buffer = []
                    length = 0
                for idx in range(0, len(paragraph), self.chunk_max_chars):
                    chunks.append(paragraph[idx : idx + self.chunk_max_chars])
                continue
            projected = length + len(paragraph) + (2 if buffer else 0)
            if buffer and projected > self.chunk_max_chars:
                chunks.append("\n\n".join(buffer))
                buffer = [paragraph]
                length = len(paragraph)
            else:
                buffer.append(paragraph)
                length = projected
        if buffer:
            chunks.append("\n\n".join(buffer))
        return chunks
