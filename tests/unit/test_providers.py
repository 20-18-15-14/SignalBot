"""Tests for the provider abstraction introduced in Phase 1 of the multi-model migration."""

import pytest

from app.core.config import Settings
from app.services.agent import AgentService
from app.services.providers import PROVIDERS, build_provider, register_provider
from app.services.providers.base import (
    ContextBlob,
    GenerationRequest,
    GenerationResponse,
    LLMProvider,
    StubProvider,
)
from app.services.providers.openai_provider import OpenAIProvider


def _settings(openai_key: str = "") -> Settings:
    return Settings(
        database_url="sqlite://",
        admin_api_token="test-token",
        signal_webhook_secret="secret",
        openai_api_key=openai_key,
    )


class _RecordingProvider:
    """Test double that records the request and returns a canned response."""

    name = "recording"

    def __init__(self):
        self.last_request: GenerationRequest | None = None

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        self.last_request = request
        return GenerationResponse(
            text="canned",
            usage={"input_tokens": 1, "output_tokens": 2},
            provider=self.name,
        )


def test_context_blob_from_group_retrieval_item():
    blob = ContextBlob.from_retrieval_item(
        {"type": "group", "group_id": "G1", "score": 0.42, "content": "hello"}
    )
    assert blob.type == "group"
    assert blob.scope == "G1"
    assert blob.score == 0.42
    assert blob.content == "hello"


def test_context_blob_from_knowledge_retrieval_item():
    blob = ContextBlob.from_retrieval_item(
        {"type": "knowledge", "scope": "global", "score": 0.7, "content": "doc"}
    )
    assert blob.scope == "global"


def test_agent_uses_stub_when_no_api_key():
    agent = AgentService(_settings(openai_key=""))
    assert isinstance(agent.provider, StubProvider)


def test_agent_passes_request_through_provider_and_preserves_sources():
    provider = _RecordingProvider()
    agent = AgentService(_settings(openai_key="sk-fake"), provider=provider)

    group_ctx = [{"type": "group", "group_id": "G1", "score": 0.5, "content": "g"}]
    knowledge_ctx = [{"type": "knowledge", "scope": "global", "score": 0.9, "content": "k"}]

    result = agent.answer(
        question="who?",
        group_context=group_ctx,
        knowledge_context=knowledge_ctx,
        authorized_group_ids=["G1"],
        privacy_mode=True,
    )

    # Contract: returns text, sources (raw retrieval dicts), usage
    assert result["text"] == "canned"
    assert result["sources"] == group_ctx + knowledge_ctx
    assert result["usage"] == {"input_tokens": 1, "output_tokens": 2}

    # Provider received a normalized request
    assert provider.last_request is not None
    assert provider.last_request.question == "who?"
    assert provider.last_request.authorized_group_ids == ["G1"]
    assert provider.last_request.privacy_mode is True
    assert len(provider.last_request.context_blobs) == 2


def test_stub_provider_matches_disabled_generation_substring():
    """The e2e test asserts 'generation is disabled' in the response. Lock it in."""
    stub = StubProvider()
    response = stub.generate(
        GenerationRequest(
            question="q",
            context_blobs=[],
            authorized_group_ids=[],
            privacy_mode=True,
        )
    )
    assert "generation is disabled" in response.text


def test_llmprovider_protocol_is_satisfied_by_stub_and_recording_providers():
    assert isinstance(StubProvider(), LLMProvider)
    assert isinstance(_RecordingProvider(), LLMProvider)


def test_openai_and_stub_are_registered_by_default():
    assert "openai" in PROVIDERS
    assert "stub" in PROVIDERS


def test_build_provider_returns_configured_instance():
    provider = build_provider("openai", _settings(openai_key="sk-fake"))
    assert isinstance(provider, OpenAIProvider)
    assert provider.name == "openai"


def test_build_provider_raises_for_unknown_name():
    with pytest.raises(KeyError):
        build_provider("does-not-exist", _settings())


def test_register_provider_makes_it_buildable():
    name = "pytest-recording"

    def factory(_settings):
        return _RecordingProvider()

    try:
        register_provider(name, factory)
        provider = build_provider(name, _settings())
        assert isinstance(provider, _RecordingProvider)
    finally:
        PROVIDERS.pop(name, None)


def test_agent_falls_back_to_stub_when_default_provider_is_unknown():
    settings = _settings()
    settings.default_provider = "not-registered"
    agent = AgentService(settings)
    assert isinstance(agent.provider, StubProvider)


def test_agent_falls_back_to_stub_when_openai_default_has_no_key():
    settings = _settings(openai_key="")
    settings.default_provider = "openai"
    agent = AgentService(settings)
    assert isinstance(agent.provider, StubProvider)


def test_agent_uses_registered_provider_when_default_matches():
    name = "pytest-default"

    def factory(_settings):
        return _RecordingProvider()

    try:
        register_provider(name, factory)
        settings = _settings()
        settings.default_provider = name
        agent = AgentService(settings)
        assert isinstance(agent.provider, _RecordingProvider)
    finally:
        PROVIDERS.pop(name, None)
