from collections.abc import Callable

from app.core.config import Settings
from app.services.providers.base import (
    ContextBlob,
    GenerationRequest,
    GenerationResponse,
    LLMProvider,
    StubProvider,
)
from app.services.providers.openai_provider import OpenAIProvider

# Registry of available provider factories. New providers register themselves here
# to become selectable via DEFAULT_PROVIDER or the router. See docs/PROVIDERS.md.
ProviderFactory = Callable[[Settings], LLMProvider]

PROVIDERS: dict[str, ProviderFactory] = {
    "openai": lambda s: OpenAIProvider(s),
    "stub": lambda _: StubProvider(),
}


def register_provider(name: str, factory: ProviderFactory) -> None:
    """Register a provider factory under a name. Intended for use by provider modules."""
    PROVIDERS[name] = factory


def build_provider(name: str, settings: Settings) -> LLMProvider:
    """Construct a provider by registered name. Raises KeyError if unknown."""
    if name not in PROVIDERS:
        raise KeyError(
            f"Unknown provider '{name}'. Registered: {sorted(PROVIDERS)}. "
            "See docs/PROVIDERS.md for how to add one."
        )
    return PROVIDERS[name](settings)


__all__ = [
    "PROVIDERS",
    "ContextBlob",
    "GenerationRequest",
    "GenerationResponse",
    "LLMProvider",
    "OpenAIProvider",
    "ProviderFactory",
    "StubProvider",
    "build_provider",
    "register_provider",
]
