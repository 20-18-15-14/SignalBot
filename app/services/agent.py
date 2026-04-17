from app.core.config import Settings
from app.services.providers import (
    PROVIDERS,
    ContextBlob,
    GenerationRequest,
    LLMProvider,
    StubProvider,
    build_provider,
)


class AgentService:
    """Coordinates retrieval context and delegates generation to a pluggable provider.

    Phase 1 of the multi-model migration: preserves the existing public contract
    (`answer()` returning `{text, sources, usage}`) while isolating provider-specific
    logic behind `providers/`. Provider selection is driven by the `default_provider`
    setting and the registry in `app.services.providers.PROVIDERS`.
    """

    def __init__(self, settings: Settings, provider: LLMProvider | None = None):
        self.settings = settings
        self.provider: LLMProvider = provider or self._resolve_provider(settings)

    @staticmethod
    def _resolve_provider(settings: Settings) -> LLMProvider:
        name = settings.default_provider
        # If the requested provider is OpenAI but no key is configured, fall back to
        # the stub so the app still boots. Any other named provider is built as-is
        # and is responsible for reporting its own misconfiguration.
        if name == "openai" and not settings.openai_api_key:
            return StubProvider()
        if name not in PROVIDERS:
            return StubProvider()
        return build_provider(name, settings)

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
