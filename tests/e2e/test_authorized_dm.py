from datetime import datetime, timezone

from app.models.enums import ChatType
from app.schemas.signal import NormalizedSignalMessage
from app.services.embeddings import EmbeddingAdapter
from app.services.memory import MemoryService


def test_authorized_user_dm_reply_flow(orchestrator, repo, fake_gateway):
    repo.set_group_state("group-auth", "authorized")
    repo.db.commit()
    memory = MemoryService(repo, EmbeddingAdapter(orchestrator.settings), orchestrator.settings.enable_dm_storage_minimal)
    group_msg = NormalizedSignalMessage(
        sender_id="user-allowed",
        chat_type=ChatType.GROUP,
        group_id="group-auth",
        body="indicator xyz linked to phishing kit",
        timestamp=datetime.now(timezone.utc),
    )
    memory.store_message(group_msg)
    repo.db.commit()
    memory.ingest_group_messages("group-auth")
    repo.db.commit()

    dm = NormalizedSignalMessage(
        sender_id="user-allowed",
        chat_type=ChatType.DIRECT,
        body="What do we know about indicator xyz?",
        timestamp=datetime.now(timezone.utc),
    )
    result = orchestrator.handle(dm)
    repo.db.commit()
    assert result["status"] == "replied"
    assert fake_gateway.sent_messages
    assert "generation is disabled" in fake_gateway.sent_messages[-1]["message"]


def test_unauthorized_user_e2e_denial(orchestrator, fake_gateway):
    dm = NormalizedSignalMessage(
        sender_id="user-no-access",
        chat_type=ChatType.DIRECT,
        body="Tell me about the case",
        timestamp=datetime.now(timezone.utc),
    )
    result = orchestrator.handle(dm)
    assert result["status"] == "denied"
    assert "Access is limited" in fake_gateway.sent_messages[-1]["message"]
