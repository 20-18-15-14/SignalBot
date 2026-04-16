from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import EmbeddingType


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    state: Mapped[str] = mapped_column(String(32), default="ingest_only", nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GroupMembershipObservation(Base):
    __tablename__ = "group_membership_observations"
    __table_args__ = (
        UniqueConstraint("user_id", "group_id", name="uq_membership_observation"),
        Index("ix_membership_last_seen", "last_seen_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    group_id: Mapped[str] = mapped_column(ForeignKey("groups.id"), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    confidence: Mapped[str] = mapped_column(String(32), default="medium", nullable=False)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class RawMessage(Base):
    __tablename__ = "raw_messages"
    __table_args__ = (
        UniqueConstraint("dedupe_key", name="uq_raw_messages_dedupe_key"),
        Index("ix_raw_messages_chat_scope", "chat_type", "group_id", "received_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dedupe_key: Mapped[str] = mapped_column(String(128), nullable=False)
    chat_type: Mapped[str] = mapped_column(String(32), nullable=False)
    group_id: Mapped[str | None] = mapped_column(ForeignKey("groups.id"), nullable=True)
    sender_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    sender_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    body: Mapped[str] = mapped_column(Text, default="", nullable=False)
    quoted_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    quoted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    stored_for_debug: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    chunked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ConversationChunk(Base):
    __tablename__ = "conversation_chunks"
    __table_args__ = (Index("ix_chunks_scope", "group_id", "start_time", "end_time"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[str] = mapped_column(ForeignKey("groups.id"), nullable=False)
    scope: Mapped[str] = mapped_column(String(64), nullable=False)
    source_message_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(EmbeddingType(), nullable=True)
    sender_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    classification_label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    collection_scope: Mapped[str] = mapped_column(String(64), nullable=False)
    group_id: Mapped[str | None] = mapped_column(ForeignKey("groups.id"), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (Index("ix_knowledge_chunks_scope", "collection_scope", "group_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("knowledge_documents.id"), nullable=False)
    collection_scope: Mapped[str] = mapped_column(String(64), nullable=False)
    group_id: Mapped[str | None] = mapped_column(ForeignKey("groups.id"), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(EmbeddingType(), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    actor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_type: Mapped[str] = mapped_column(String(64), nullable=False)
    scope_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
