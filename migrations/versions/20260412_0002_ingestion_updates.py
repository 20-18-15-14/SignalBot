"""ingestion updates"""

from alembic import op
import sqlalchemy as sa


revision = "20260412_0002"
down_revision = "20260410_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("raw_messages", sa.Column("chunked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ingestion_jobs", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ingestion_jobs", sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ingestion_jobs", sa.Column("error", sa.String(length=1000), nullable=True))
    op.create_index("ix_ingestion_jobs_status", "ingestion_jobs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_ingestion_jobs_status", table_name="ingestion_jobs")
    op.drop_column("ingestion_jobs", "error")
    op.drop_column("ingestion_jobs", "finished_at")
    op.drop_column("ingestion_jobs", "started_at")
    op.drop_column("raw_messages", "chunked_at")
