from datetime import datetime, timezone
from hashlib import sha256

from pydantic import BaseModel, Field

from app.models.enums import ChatType


class SignalQuote(BaseModel):
    message_id: str | None = None
    text: str | None = None


class NormalizedSignalMessage(BaseModel):
    message_id: str | None = None
    sender_id: str
    sender_name: str | None = None
    chat_type: ChatType
    group_id: str | None = None
    group_title: str | None = None
    body: str = ""
    timestamp: datetime
    quote: SignalQuote | None = None
    attachments: list[dict] = Field(default_factory=list)
    mentions: list[dict] = Field(default_factory=list)
    reaction: dict | None = None
    raw_payload: dict = Field(default_factory=dict)

    def dedupe_key(self) -> str:
        normalized = "|".join(
            [
                self.sender_id,
                self.chat_type.value,
                self.group_id or "",
                self.timestamp.astimezone(timezone.utc).isoformat(),
                self.body.strip(),
                self.message_id or "",
            ]
        )
        return sha256(normalized.encode("utf-8")).hexdigest()
