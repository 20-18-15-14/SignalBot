from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import orchestrator_dependency, repository_dependency, settings_dependency
from app.core.config import Settings
from app.db.base import Base
from app.main import app
from app.services.agent import AgentService
from app.services.embeddings import EmbeddingAdapter
from app.services.memory import MemoryService
from app.services.orchestrator import InboundMessageOrchestrator
from app.services.policy_engine import PolicyEngine
from app.services.repositories import Repository
from app.services.signal_gateway import SignalGateway


TEST_SETTINGS = Settings(
    database_url="sqlite://",
    admin_api_token="test-token",
    signal_webhook_secret="secret",
    enable_dm_storage_minimal=True,
    openai_api_key="",
)


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def repo(db_session: Session) -> Repository:
    return Repository(db_session)


class FakeSignalGateway(SignalGateway):
    def __init__(self, settings: Settings):
        super().__init__(settings)
        self.sent_messages: list[dict] = []

    def send_message(self, recipient: str, message: str, group_id: str | None = None) -> dict:
        payload = {"recipient": recipient, "message": message, "group_id": group_id}
        self.sent_messages.append(payload)
        return payload

    def health(self) -> str:
        return "ok"


@pytest.fixture()
def fake_gateway() -> FakeSignalGateway:
    return FakeSignalGateway(TEST_SETTINGS)


@pytest.fixture()
def orchestrator(repo: Repository, fake_gateway: FakeSignalGateway) -> InboundMessageOrchestrator:
    policy = PolicyEngine(
        repo,
        TEST_SETTINGS.auth_membership_ttl_days,
        TEST_SETTINGS.enable_group_auto_reply,
        TEST_SETTINGS.group_auto_reply_only_authorized,
    )
    memory = MemoryService(repo, EmbeddingAdapter(TEST_SETTINGS), TEST_SETTINGS.enable_dm_storage_minimal)
    agent = AgentService(TEST_SETTINGS)
    from app.services.rate_limiter import RateLimiter

    return InboundMessageOrchestrator(
        TEST_SETTINGS, repo, policy, memory, agent, fake_gateway, RateLimiter()
    )


@pytest.fixture()
def client(db_session: Session, fake_gateway: FakeSignalGateway) -> Generator[TestClient, None, None]:
    def _settings_override() -> Settings:
        return TEST_SETTINGS

    def _repo_override() -> Repository:
        return Repository(db_session)

    def _orchestrator_override() -> InboundMessageOrchestrator:
        repo = Repository(db_session)
        policy = PolicyEngine(
            repo,
            TEST_SETTINGS.auth_membership_ttl_days,
            TEST_SETTINGS.enable_group_auto_reply,
            TEST_SETTINGS.group_auto_reply_only_authorized,
        )
        memory = MemoryService(repo, EmbeddingAdapter(TEST_SETTINGS), TEST_SETTINGS.enable_dm_storage_minimal)
        agent = AgentService(TEST_SETTINGS)
        from app.services.rate_limiter import RateLimiter

        return InboundMessageOrchestrator(
            TEST_SETTINGS, repo, policy, memory, agent, fake_gateway, RateLimiter()
        )

    app.dependency_overrides[settings_dependency] = _settings_override
    app.dependency_overrides[repository_dependency] = _repo_override
    app.dependency_overrides[orchestrator_dependency] = _orchestrator_override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
