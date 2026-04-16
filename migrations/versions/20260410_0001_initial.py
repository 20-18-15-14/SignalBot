"""initial schema"""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


revision = "20260410_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "groups",
        sa.Column("id", sa.String(length=255), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("state", sa.String(length=32), nullable=False, server_default="ingest_only"),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=255), primary_key=True),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "group_membership_observations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.String(length=255), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("group_id", sa.String(length=255), sa.ForeignKey("groups.id"), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confidence", sa.String(length=32), nullable=False, server_default="medium"),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.UniqueConstraint("user_id", "group_id", name="uq_membership_observation"),
    )
    op.create_index("ix_membership_last_seen", "group_membership_observations", ["last_seen_at"])
    op.create_table(
        "raw_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("external_message_id", sa.String(length=255), nullable=True),
        sa.Column("dedupe_key", sa.String(length=128), nullable=False),
        sa.Column("chat_type", sa.String(length=32), nullable=False),
        sa.Column("group_id", sa.String(length=255), sa.ForeignKey("groups.id"), nullable=True),
        sa.Column("sender_id", sa.String(length=255), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("sender_name", sa.String(length=255), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("quoted_message_id", sa.String(length=255), nullable=True),
        sa.Column("quoted_text", sa.Text(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("stored_for_debug", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("dedupe_key", name="uq_raw_messages_dedupe_key"),
    )
    op.create_index("ix_raw_messages_chat_scope", "raw_messages", ["chat_type", "group_id", "received_at"])
    op.create_table(
        "conversation_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("group_id", sa.String(length=255), sa.ForeignKey("groups.id"), nullable=False),
        sa.Column("scope", sa.String(length=64), nullable=False),
        sa.Column("source_message_ids", sa.JSON(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(dim=1536), nullable=True),
        sa.Column("sender_ids", sa.JSON(), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_chunks_scope", "conversation_chunks", ["group_id", "start_time", "end_time"])
    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("classification_label", sa.String(length=128), nullable=True),
        sa.Column("collection_scope", sa.String(length=64), nullable=False),
        sa.Column("group_id", sa.String(length=255), sa.ForeignKey("groups.id"), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("knowledge_documents.id"), nullable=False),
        sa.Column("collection_scope", sa.String(length=64), nullable=False),
        sa.Column("group_id", sa.String(length=255), sa.ForeignKey("groups.id"), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(dim=1536), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_knowledge_chunks_scope", "knowledge_chunks", ["collection_scope", "group_id"])
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_conversation_chunks_embedding_hnsw "
        "ON conversation_chunks USING hnsw (embedding vector_cosine_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_embedding_hnsw "
        "ON knowledge_chunks USING hnsw (embedding vector_cosine_ops)"
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("actor", sa.String(length=255), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "ingestion_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column("scope_id", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("ingestion_jobs")
    op.drop_table("audit_logs")
    op.drop_index("ix_knowledge_chunks_scope", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
    op.drop_table("knowledge_documents")
    op.drop_index("ix_chunks_scope", table_name="conversation_chunks")
    op.drop_table("conversation_chunks")
    op.drop_index("ix_raw_messages_chat_scope", table_name="raw_messages")
    op.drop_table("raw_messages")
    op.drop_index("ix_membership_last_seen", table_name="group_membership_observations")
    op.drop_table("group_membership_observations")
    op.drop_table("users")
    op.drop_table("groups")
