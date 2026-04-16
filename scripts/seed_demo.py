from datetime import datetime, timezone

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.enums import ChatType
from app.schemas.signal import NormalizedSignalMessage
from app.services.embeddings import EmbeddingAdapter
from app.services.memory import MemoryService
from app.services.repositories import Repository


def main() -> int:
    settings = get_settings()
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        repo = Repository(db)
        memory = MemoryService(
            repo,
            EmbeddingAdapter(settings),
            settings.enable_dm_storage_minimal,
            settings.chunk_max_chars,
            settings.chunk_max_messages,
        )
        repo.set_group_state("group-authorized", "authorized")
        repo.set_group_state("group-ingest-only", "ingest_only")
        messages = [
            NormalizedSignalMessage(
                sender_id="user-allowed",
                sender_name="Allowed User",
                chat_type=ChatType.GROUP,
                group_id="group-authorized",
                group_title="Authorized Group",
                body="Threat feed says host alpha resolved suspicious infrastructure yesterday.",
                timestamp=datetime.now(timezone.utc),
                raw_payload={"demo": True},
            ),
            NormalizedSignalMessage(
                sender_id="user-denied",
                sender_name="Denied User",
                chat_type=ChatType.GROUP,
                group_id="group-ingest-only",
                group_title="Ingest Only Group",
                body="Ops note about routine maintenance window.",
                timestamp=datetime.now(timezone.utc),
                raw_payload={"demo": True},
            ),
        ]
        for message in messages:
            memory.store_message(message)
        memory.ingest_group_messages("group-authorized")
        memory.ingest_group_messages("group-ingest-only")
        db.commit()
    print("Seeded demo data for two groups, one authorized user, and one denied user.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
