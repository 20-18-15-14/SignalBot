from collections import defaultdict
from datetime import datetime

from app.schemas.signal import NormalizedSignalMessage
from app.services.embeddings import EmbeddingAdapter
from app.services.repositories import Repository


class MemoryService:
    def __init__(
        self,
        repository: Repository,
        embeddings: EmbeddingAdapter,
        enable_dm_storage_minimal: bool,
        chunk_max_chars: int = 3500,
        chunk_max_messages: int = 50,
    ):
        self.repository = repository
        self.embeddings = embeddings
        self.enable_dm_storage_minimal = enable_dm_storage_minimal
        self.chunk_max_chars = max(500, chunk_max_chars)
        self.chunk_max_messages = max(5, chunk_max_messages)

    def store_message(self, message: NormalizedSignalMessage) -> bool:
        if self.repository.find_raw_message_by_dedupe(message.dedupe_key()):
            return False

        if message.group_id:
            self.repository.upsert_group(message.group_id, message.group_title)
            self.repository.record_membership(
                user_id=message.sender_id,
                group_id=message.group_id,
                evidence={"source": "group_message", "message_id": message.message_id},
            )
        self.repository.upsert_user(message.sender_id, message.sender_name)

        store_debug = self.enable_dm_storage_minimal or message.chat_type.value == "group"
        if message.chat_type.value == "direct" and not self.enable_dm_storage_minimal:
            return True

        self.repository.store_raw_message(message, debug_storage_enabled=store_debug)
        return True

    def ingest_group_messages(self, group_id: str) -> int:
        total_chunks = 0
        while True:
            messages = self.repository.list_group_messages_without_chunks(group_id)
            if not messages:
                return total_chunks
            grouped: dict[str, list] = defaultdict(list)
            for message in messages:
                key = message.received_at.date().isoformat()
                grouped[key].append(message)

            for _, group_messages in grouped.items():
                buffer_lines: list[str] = []
                buffer_ids: list[int] = []
                buffer_senders: set[str] = set()
                buffer_length = 0
                start_time = None
                chunk_index = 0

                def flush_chunk(end_time):
                    nonlocal total_chunks, chunk_index, buffer_lines, buffer_ids, buffer_senders, start_time, buffer_length
                    if not buffer_lines:
                        return
                    content = "\n".join(buffer_lines)
                    embedding = self.embeddings.embed_text(content)
                    self.repository.create_chunk(
                        group_id=group_id,
                        content=content,
                        source_message_ids=list(buffer_ids),
                        sender_ids=list(buffer_senders),
                        start_time=start_time,
                        end_time=end_time,
                        metadata_json={
                            "message_count": len(buffer_ids),
                            "group_id": group_id,
                            "conversation_style": "day_window",
                            "chunk_index": chunk_index,
                        },
                        embedding=embedding,
                    )
                    self.repository.mark_messages_chunked(buffer_ids)
                    total_chunks += 1
                    chunk_index += 1
                    buffer_lines = []
                    buffer_ids = []
                    buffer_senders = set()
                    start_time = None
                    buffer_length = 0

                for msg in group_messages:
                    line = f"[{msg.received_at.isoformat()}] {msg.sender_name or msg.sender_id}: {msg.body}"
                    projected_length = buffer_length + len(line) + (1 if buffer_lines else 0)
                    if buffer_lines and (
                        projected_length > self.chunk_max_chars or len(buffer_ids) >= self.chunk_max_messages
                    ):
                        flush_chunk(msg.received_at)
                    if start_time is None:
                        start_time = msg.received_at
                    buffer_lines.append(line)
                    buffer_ids.append(msg.id)
                    buffer_senders.add(msg.sender_id)
                    buffer_length = projected_length

                if buffer_lines:
                    flush_chunk(group_messages[-1].received_at)

    def retrieve_group_context(
        self,
        query: str,
        group_ids: list[str],
        sender_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 5,
    ) -> list[dict]:
        query_embedding = self.embeddings.embed_text(query)
        scored = self.repository.search_chunks_by_embedding(
            query_embedding=query_embedding,
            group_ids=group_ids,
            sender_id=sender_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )
        if self.repository.db.bind and self.repository.db.bind.dialect.name != "postgresql":
            rescored = [
                (chunk, self.embeddings.cosine_similarity(query_embedding, chunk.embedding))
                for chunk, _ in scored
            ]
            rescored.sort(key=lambda item: item[1], reverse=True)
            scored = rescored[:limit]
        return [
            {
                "type": "group_memory",
                "group_id": chunk.group_id,
                "content": chunk.content,
                "score": score,
                "metadata": chunk.metadata_json,
            }
            for chunk, score in scored[:limit]
        ]

    def retrieve_knowledge_context(self, query: str, scopes: list[str], group_ids: list[str], limit: int = 5) -> list[dict]:
        query_embedding = self.embeddings.embed_text(query)
        scored = self.repository.search_knowledge_by_embedding(
            query_embedding=query_embedding,
            scopes=scopes,
            group_ids=group_ids,
            limit=limit,
        )
        if self.repository.db.bind and self.repository.db.bind.dialect.name != "postgresql":
            rescored = [
                (chunk, self.embeddings.cosine_similarity(query_embedding, chunk.embedding))
                for chunk, _ in scored
            ]
            rescored.sort(key=lambda item: item[1], reverse=True)
            scored = rescored[:limit]
        return [
            {
                "type": "knowledge",
                "scope": chunk.collection_scope,
                "group_id": chunk.group_id,
                "content": chunk.content,
                "score": score,
                "metadata": chunk.metadata_json,
            }
            for chunk, score in scored[:limit]
        ]
