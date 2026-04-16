from datetime import datetime

from pydantic import BaseModel


class GroupResponse(BaseModel):
    id: str
    title: str | None
    state: str
    last_seen_at: datetime | None


class UserAccessResponse(BaseModel):
    user_id: str
    eligible: bool
    authorized_group_ids: list[str]
    ingest_only_group_ids: list[str]
    confidence: str


class HealthResponse(BaseModel):
    status: str
    signal_gateway: str
    database: str
