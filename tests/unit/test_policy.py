from datetime import datetime, timezone

from app.models.enums import ChatType
from app.schemas.signal import NormalizedSignalMessage
from app.services.policy_engine import PolicyEngine


def test_group_messages_are_ingested(repo):
    repo.set_group_state("group-1", "authorized")
    engine = PolicyEngine(
        repo,
        membership_ttl_days=30,
        enable_group_auto_reply=False,
        group_auto_reply_only_authorized=True,
    )
    message = NormalizedSignalMessage(
        sender_id="user-1",
        chat_type=ChatType.GROUP,
        group_id="group-1",
        body="hello",
        timestamp=datetime.now(timezone.utc),
    )
    decision = engine.evaluate(message)
    assert decision.ingest is True
    assert decision.respond is False


def test_authorized_dm_can_reply(repo):
    repo.set_group_state("group-1", "authorized")
    repo.upsert_user("user-1", "Test User")
    repo.record_membership("user-1", "group-1", {"source": "test"})
    repo.db.commit()
    engine = PolicyEngine(
        repo,
        membership_ttl_days=30,
        enable_group_auto_reply=False,
        group_auto_reply_only_authorized=True,
    )
    message = NormalizedSignalMessage(
        sender_id="user-1",
        chat_type=ChatType.DIRECT,
        body="what happened?",
        timestamp=datetime.now(timezone.utc),
    )
    decision = engine.evaluate(message)
    assert decision.respond is True
    assert decision.authorized_group_ids == ["group-1"]


def test_ingest_only_user_cannot_dm(repo):
    repo.set_group_state("group-2", "ingest_only")
    repo.upsert_user("user-2", "Test User")
    repo.record_membership("user-2", "group-2", {"source": "test"})
    repo.db.commit()
    engine = PolicyEngine(
        repo,
        membership_ttl_days=30,
        enable_group_auto_reply=False,
        group_auto_reply_only_authorized=True,
    )
    message = NormalizedSignalMessage(
        sender_id="user-2",
        chat_type=ChatType.DIRECT,
        body="help",
        timestamp=datetime.now(timezone.utc),
    )
    decision = engine.evaluate(message)
    assert decision.respond is False
    assert decision.reason == "dm_not_authorized"
