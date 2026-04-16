from datetime import datetime, timezone

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed

from app.core.config import Settings
from app.models.enums import ChatType
from app.schemas.signal import NormalizedSignalMessage, SignalQuote


class SignalGateway:
    def __init__(self, settings: Settings):
        self.settings = settings

    def normalize_event(self, payload: dict) -> NormalizedSignalMessage:
        envelope = payload.get("envelope", payload)
        data_message = envelope.get("dataMessage", {})
        group_info = data_message.get("groupInfo") or {}
        group_id = group_info.get("groupId") or envelope.get("groupId")
        quote = data_message.get("quote") or {}
        attachments = data_message.get("attachments") or []
        mentions = data_message.get("mentions") or []
        reaction = data_message.get("reaction")
        timestamp_ms = envelope.get("timestamp") or data_message.get("timestamp") or 0
        timestamp = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
        chat_type = ChatType.GROUP if group_id else ChatType.DIRECT
        body = data_message.get("message", "") or ""
        if attachments:
            summaries = []
            for attachment in attachments:
                name = attachment.get("fileName") or attachment.get("filename") or "attachment"
                content_type = attachment.get("contentType") or attachment.get("content_type") or "unknown"
                size = attachment.get("size")
                size_part = f", {size} bytes" if size else ""
                summaries.append(f"[attachment] {name} ({content_type}{size_part})")
            attachment_block = "\n".join(summaries)
            body = f"{body}\n{attachment_block}".strip()
        if reaction and not body:
            emoji = reaction.get("emoji") or "reaction"
            target = reaction.get("targetAuthor") or reaction.get("target_author") or "unknown"
            body = f"[reaction] {emoji} -> {target}"
        return NormalizedSignalMessage(
            message_id=str(envelope.get("sourceDevice", "")) + ":" + str(timestamp_ms),
            sender_id=envelope.get("source") or envelope.get("sender") or "unknown",
            sender_name=envelope.get("sourceName") or envelope.get("senderName"),
            chat_type=chat_type,
            group_id=group_id,
            group_title=group_info.get("groupName"),
            body=body,
            timestamp=timestamp,
            quote=SignalQuote(message_id=str(quote.get("id")) if quote.get("id") else None, text=quote.get("text")),
            attachments=attachments,
            mentions=mentions,
            reaction=reaction,
            raw_payload=payload,
        )

    @retry(wait=wait_fixed(2), stop=stop_after_attempt(3))
    def send_message(self, recipient: str, message: str, group_id: str | None = None) -> dict:
        payload = {"message": message, "number": self.settings.signal_bot_number}
        payload["recipient"] = group_id if group_id else recipient
        with httpx.Client(timeout=10) as client:
            response = client.post(f"{self.settings.signal_api_base_url}/v2/send", json=payload)
            response.raise_for_status()
            return response.json()

    def health(self) -> str:
        try:
            with httpx.Client(timeout=5) as client:
                response = client.get(f"{self.settings.signal_api_base_url}/v1/health")
                response.raise_for_status()
            return "ok"
        except Exception:
            return "degraded"
