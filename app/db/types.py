from sqlalchemy import JSON
from sqlalchemy.types import TypeDecorator

from app.core.config import get_settings

try:
    from pgvector.sqlalchemy import Vector
except ImportError:  # pragma: no cover - handled by dependency installation
    Vector = None


class EmbeddingType(TypeDecorator):
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        settings = get_settings()
        if dialect.name == "postgresql" and Vector is not None:
            return dialect.type_descriptor(Vector(settings.embedding_dimensions))
        return dialect.type_descriptor(JSON())
