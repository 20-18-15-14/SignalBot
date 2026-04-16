import time
from datetime import datetime, timezone

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.embeddings import EmbeddingAdapter
from app.services.memory import MemoryService
from app.services.repositories import Repository


def run_worker() -> None:
    settings = get_settings()
    poll_seconds = max(1, settings.ingestion_worker_poll_seconds)
    batch_size = max(1, settings.ingestion_worker_batch_size)

    while True:
        with SessionLocal() as db:
            repo = Repository(db)
            memory = MemoryService(
                repo,
                EmbeddingAdapter(settings),
                settings.enable_dm_storage_minimal,
                settings.chunk_max_chars,
                settings.chunk_max_messages,
            )
            jobs = repo.claim_pending_jobs(limit=batch_size)
            if not jobs:
                db.commit()
                time.sleep(poll_seconds)
                continue

            db.commit()
            for job in jobs:
                try:
                    if job.job_type == "reindex" and job.scope_id:
                        repo.clear_chunks_for_group(job.scope_id)
                        repo.reset_chunked_messages(job.scope_id)
                        memory.ingest_group_messages(job.scope_id)
                    elif job.job_type == "ingest_group" and job.scope_id:
                        memory.ingest_group_messages(job.scope_id)
                    repo.mark_job_succeeded(job)
                    job.details = {**(job.details or {}), "completed_at": datetime.now(timezone.utc).isoformat()}
                    db.commit()
                except Exception as exc:  # pragma: no cover - operational safety
                    repo.mark_job_failed(job, str(exc))
                    db.commit()


def main() -> None:
    run_worker()


if __name__ == "__main__":
    main()
