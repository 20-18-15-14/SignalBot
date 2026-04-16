from app.core.config import Settings
from app.models.enums import ChatType
from app.services.signal_gateway import SignalGateway


def test_signal_payload_normalization_extracts_group_metadata():
    gateway = SignalGateway(Settings())
    payload = {
        "envelope": {
            "source": "+15551112222",
            "sourceName": "Alice",
            "sourceDevice": 1,
            "timestamp": 1712700000000,
            "dataMessage": {
                "message": "intel update",
                "groupInfo": {"groupId": "group-123", "groupName": "Ops"},
                "quote": {"id": 99, "text": "previous"},
            },
        }
    }
    normalized = gateway.normalize_event(payload)
    assert normalized.chat_type == ChatType.GROUP
    assert normalized.group_id == "group-123"
    assert normalized.quote and normalized.quote.message_id == "99"
