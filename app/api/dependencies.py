from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.services.agent import AgentService
from app.services.embeddings import EmbeddingAdapter
from app.services.knowledge_ingest import KnowledgeIngestService
from app.services.memory import MemoryService
from app.services.orchestrator import InboundMessageOrchestrator
from app.services.policy_engine import PolicyEngine
from app.services.repositories import Repository
from app.services.signal_gateway import SignalGateway


def settings_dependency() -> Settings:
    return get_settings()


def admin_auth(
    settings: Settings = Depends(settings_dependency),
    authorization: str | None = Header(default=None),
) -> None:
    tokens = settings.admin_token_list()
    if not tokens:
        raise HTTPException(status_code=500, detail="admin auth is not configured")
    if authorization is None:
        raise HTTPException(status_code=401, detail="unauthorized")
    expected_values = {f"Bearer {token}" for token in tokens}
    if authorization not in expected_values:
        raise HTTPException(status_code=401, detail="unauthorized")


def repository_dependency(db: Session = Depends(get_db)) -> Repository:
    return Repository(db)


def orchestrator_dependency(
    repo: Repository = Depends(repository_dependency),
    settings: Settings = Depends(settings_dependency),
) -> InboundMessageOrchestrator:
    policy = PolicyEngine(
        repo,
        settings.auth_membership_ttl_days,
        settings.enable_group_auto_reply,
        settings.group_auto_reply_only_authorized,
    )
    memory = MemoryService(
        repo,
        EmbeddingAdapter(settings),
        settings.enable_dm_storage_minimal,
        settings.chunk_max_chars,
        settings.chunk_max_messages,
    )
    agent = AgentService(settings)
    signal_gateway = SignalGateway(settings)
    from app.services.rate_limiter import GLOBAL_RATE_LIMITER

    return InboundMessageOrchestrator(settings, repo, policy, memory, agent, signal_gateway, GLOBAL_RATE_LIMITER)


def knowledge_dependency(
    repo: Repository = Depends(repository_dependency),
    settings: Settings = Depends(settings_dependency),
) -> KnowledgeIngestService:
    return KnowledgeIngestService(repo, EmbeddingAdapter(settings), settings.knowledge_chunk_max_chars)
