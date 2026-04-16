from dataclasses import dataclass

from app.models.enums import ChatType, GroupState
from app.schemas.signal import NormalizedSignalMessage
from app.services.repositories import Repository


@dataclass
class PolicyDecision:
    ingest: bool
    respond: bool
    reason: str
    authorized_group_ids: list[str]


class PolicyEngine:
    def __init__(
        self,
        repository: Repository,
        membership_ttl_days: int,
        enable_group_auto_reply: bool,
        group_auto_reply_only_authorized: bool,
    ):
        self.repository = repository
        self.membership_ttl_days = membership_ttl_days
        self.enable_group_auto_reply = enable_group_auto_reply
        self.group_auto_reply_only_authorized = group_auto_reply_only_authorized

    def evaluate(self, message: NormalizedSignalMessage) -> PolicyDecision:
        if message.chat_type == ChatType.GROUP:
            group = self.repository.upsert_group(message.group_id or "unknown", message.group_title)
            if group.state == GroupState.IGNORED.value:
                return PolicyDecision(ingest=False, respond=False, reason="group_ignored", authorized_group_ids=[])
            authorized = group.state == GroupState.AUTHORIZED.value
            respond = self.enable_group_auto_reply and (authorized or not self.group_auto_reply_only_authorized)
            reason = "group_ingest_only"
            if respond and authorized:
                reason = "group_auto_reply_authorized"
            elif respond:
                reason = "group_auto_reply_enabled"
            return PolicyDecision(
                ingest=True,
                respond=respond,
                reason=reason,
                authorized_group_ids=[group.id] if authorized else [],
            )

        access = self.repository.user_access_snapshot(message.sender_id, self.membership_ttl_days)
        if access["eligible"]:
            return PolicyDecision(
                ingest=False,
                respond=True,
                reason="authorized_dm",
                authorized_group_ids=access["authorized_group_ids"],
            )
        return PolicyDecision(ingest=False, respond=False, reason="dm_not_authorized", authorized_group_ids=[])
