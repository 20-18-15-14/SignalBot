from hashlib import sha256
from math import sqrt

from openai import OpenAI

from app.core.config import Settings


class EmbeddingAdapter:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = (
            OpenAI(api_key=settings.openai_api_key, timeout=settings.openai_request_timeout_seconds)
            if settings.openai_api_key
            else None
        )

    def embed_text(self, text: str) -> list[float]:
        if not text.strip():
            return [0.0] * self.settings.embedding_dimensions
        if self.client is None:
            return self._local_stub_embedding(text)
        response = self.client.embeddings.create(model=self.settings.openai_embedding_model, input=text)
        return list(response.data[0].embedding)

    def cosine_similarity(self, left: list[float] | None, right: list[float] | None) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        dot = sum(a * b for a, b in zip(left, right, strict=True))
        left_norm = sqrt(sum(a * a for a in left))
        right_norm = sqrt(sum(b * b for b in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return dot / (left_norm * right_norm)

    def _local_stub_embedding(self, text: str) -> list[float]:
        dims = self.settings.embedding_dimensions
        digest = sha256(text.encode("utf-8")).digest()
        values: list[float] = []
        idx = 0
        while len(values) < dims:
            if idx >= len(digest):
                digest = sha256(digest + text.encode("utf-8")).digest()
                idx = 0
            values.append(digest[idx] / 255.0)
            idx += 1
        return values
