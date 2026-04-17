from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class ContextBlob:
    type: str
    scope: str
    score: float
    content: str

    @classmethod
    def from_retrieval_item(cls, item: dict) -> "ContextBlob":
        return cls(
            type=item["type"],
            scope=item.get("group_id") or item.get("scope") or "",
            score=float(item["score"]),
            content=item["content"],
        )


@dataclass
class GenerationRequest:
    question: str
    context_blobs: list[ContextBlob]
    authorized_group_ids: list[str]
    privacy_mode: bool
    web_search_enabled: bool = False
    metadata: dict = field(default_factory=dict)


@dataclass
class GenerationResponse:
    text: str
    usage: dict
    provider: str = ""


@runtime_checkable
class LLMProvider(Protocol):
    name: str

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        ...


class StubProvider:
    """Used when no provider is configured. Returns a placeholder so the rest of the pipeline still works."""

    name = "stub"

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        return GenerationResponse(
            text="No language model provider is configured. Retrieval succeeded, but generation is disabled.",
            usage={},
            provider=self.name,
        )
