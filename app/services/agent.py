from app.core.config import Settings
from app.services.providers.base import (
    ContextBlob,
    GenerationRequest,
    LLMProvider,
    StubProvider,
)
from app.services.providers.openai_provider import OpenAIProvider


class AgentService:
    """Coordinates retrieval context and delegates generation to a pluggable provider.

    Phase 1 of the multi-model migration: preserves the existing public contract
    (`answer()` returning `{text, sources, usage}`) while isolating provider-specific
    logic behind `providers/`.
    """

    def __init__(self, settings: Settings, provider: LLMProvider | None = None):
        self.settings = settings
        self.provider: LLMProvider = provider or self._default_provider(settings)

    @staticmethod
    def _default_provider(settings: Settings) -> LLMProvider:
        if settings.openai_api_key:
            return OpenAIProvider(settings)
        return StubProvider()

    def answer(
        self,
        question: str,
        group_context: list[dict],
        knowledge_context: list[dict],
        authorized_group_ids: list[str],
        privacy_mode: bool = True,
    ) -> dict:
        blobs = [ContextBlob.from_retrieval_item(item) for item in group_context + knowledge_context]
        request = GenerationRequest(
            question=question,
            context_blobs=blobs,
            authorized_group_ids=authorized_group_ids,
            privacy_mode=privacy_mode,
            web_search_enabled=self.settings.web_search_enabled,
        )
        response = self.provider.generate(request)
        return {
            "text": response.text,
            "sources": group_context + knowledge_context,
            "usage": response.usage,
        }
