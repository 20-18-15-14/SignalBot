from datetime import datetime, timezone

from app.core.config import Settings
from app.models.enums import ChatType
from app.schemas.signal import NormalizedSignalMessage
from app.services.embeddings import EmbeddingAdapter
from app.services.memory import MemoryService


def test_dm_is_never_embedded_into_shared_memory(repo):
    service = MemoryService(repo, EmbeddingAdapter(Settings()), enable_dm_storage_minimal=True)
    dm = NormalizedSignalMessage(
        sender_id="user-1",
        chat_type=ChatType.DIRECT,
        body="private question",
        timestamp=datetime.now(timezone.utc),
    )
    service.store_message(dm)
    repo.db.commit()
    assert repo.search_chunks(["any"]) == []


def test_group_message_is_embedded_and_retrievable(repo):
    service = MemoryService(repo, EmbeddingAdapter(Settings()), enable_dm_storage_minimal=True)
    msg = NormalizedSignalMessage(
        sender_id="user-1",
        sender_name="Alice",
        chat_type=ChatType.GROUP,
        group_id="group-1",
        group_title="Ops",
        body="malware beacon observed on host bravo",
        timestamp=datetime.now(timezone.utc),
    )
    service.store_message(msg)
    repo.db.commit()
    count = service.ingest_group_messages("group-1")
    repo.db.commit()
    results = service.retrieve_group_context("beacon host", ["group-1"])
    assert count == 1
    assert len(results) == 1
    assert "host bravo" in results[0]["content"]


def test_retrieved_context_respects_permitted_scopes(repo):
    service = MemoryService(repo, EmbeddingAdapter(Settings()), enable_dm_storage_minimal=True)
    for group_id, body in [("group-a", "threat actor alpha"), ("group-b", "internal budget memo")]:
        msg = NormalizedSignalMessage(
            sender_id=f"user-{group_id}",
            chat_type=ChatType.GROUP,
            group_id=group_id,
            body=body,
            timestamp=datetime.now(timezone.utc),
        )
        service.store_message(msg)
        repo.db.commit()
        service.ingest_group_messages(group_id)
        repo.db.commit()
    results = service.retrieve_group_context("threat actor", ["group-a"])
    assert len(results) == 1
    assert results[0]["group_id"] == "group-a"
