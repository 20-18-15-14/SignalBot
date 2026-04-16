from pathlib import Path

import typer

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.services.embeddings import EmbeddingAdapter
from app.services.knowledge_ingest import KnowledgeIngestService
from app.services.memory import MemoryService
from app.services.repositories import Repository

app = typer.Typer(help="Administrative CLI for signal-osint-agent")


@app.command("init-db")
def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    typer.echo("database schema created")


@app.command("reembed")
def reembed(group_id: str) -> None:
    settings = get_settings()
    with SessionLocal() as db:
        repo = Repository(db)
        memory = MemoryService(
            repo,
            EmbeddingAdapter(settings),
            settings.enable_dm_storage_minimal,
            settings.chunk_max_chars,
            settings.chunk_max_messages,
        )
        count = memory.ingest_group_messages(group_id)
        db.commit()
    typer.echo(f"reindexed {count} chunks for {group_id}")


@app.command("add-knowledge")
def add_knowledge(path: Path, collection_scope: str = "global", group_id: str | None = None) -> None:
    settings = get_settings()
    with SessionLocal() as db:
        repo = Repository(db)
        service = KnowledgeIngestService(repo, EmbeddingAdapter(settings), settings.knowledge_chunk_max_chars)
        count = service.ingest_file(path, collection_scope=collection_scope, group_id=group_id)
        db.commit()
    typer.echo(f"ingested {count} chunks from {path.name}")


@app.command("worker")
def ingestion_worker() -> None:
    from app.workers.ingestion_worker import run_worker

    run_worker()
