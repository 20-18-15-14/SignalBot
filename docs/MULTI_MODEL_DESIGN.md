# Multi-Model Design

Design doc for the Model Integration lane. Draft — revise as implementation proceeds.

## Goal

Replace `app/services/agent.py`'s hardcoded OpenAI client with a provider-agnostic abstraction that supports Anthropic, OpenAI, Gemini, and local (Ollama) while preserving the existing `AgentService.answer()` contract.

## Principles

1. **Thin abstraction.** No framework lock-in. Provider implementations are small adapters.
2. **Backward compatible.** OpenAI stays a valid provider and can be the default. No upstream consumer sees a behavior change if they keep the default.
3. **Contract preserved.** `answer()` returns `{text, sources, usage}` regardless of provider.
4. **Config-driven routing.** Provider selection and routing rules live in config, not code.
5. **Tool calls normalized.** Each provider adapter is responsible for translating to its native tool schema.

## Proposed structure

```
app/services/
├── agent.py                      # Thin orchestrator, calls into providers via the registry
├── providers/
│   ├── __init__.py               # Registry + factory
│   ├── base.py                   # LLMProvider protocol + shared types
│   ├── openai_provider.py        # Current Responses API behavior, isolated
│   ├── anthropic_provider.py     # Claude via Messages API
│   ├── gemini_provider.py        # Google GenAI
│   └── ollama_provider.py        # Local models
├── router.py                     # Selects a provider per request
└── model_usage.py                # Usage / cost / latency logging
```

## Provider contract (`base.py`)

```python
class LLMProvider(Protocol):
    name: str
    def generate(self, request: GenerationRequest) -> GenerationResponse: ...

@dataclass
class GenerationRequest:
    system: str
    user_message: str
    context_blobs: list[ContextBlob]
    tools: list[ToolSpec]        # Normalized
    privacy_mode: bool
    metadata: dict

@dataclass
class GenerationResponse:
    text: str
    sources: list[dict]
    usage: dict                   # Normalized: input_tokens, output_tokens, model, latency_ms
    provider: str
    raw: dict                     # Provider-specific response for debugging
```

## Router (`router.py`)

Rules evaluated in order; first match wins. Example config:

```yaml
routes:
  - when: { privacy_mode: true }
    provider: ollama              # DMs stay local
  - when: { needs_web_search: true }
    provider: openai              # Built-in web_search tool
  - when: { tokens_estimated: ">32000" }
    provider: anthropic           # Long context
  - default: anthropic
fallbacks:
  anthropic: [openai, gemini]
  openai:    [anthropic]
  gemini:    [anthropic, openai]
  ollama:    []                   # No fallback for privacy-sensitive routes
```

## Tool calling

Translate a single `ToolSpec` set into each provider's schema:

- OpenAI: Responses API tool objects
- Anthropic: Messages API `tools` array
- Gemini: `function_declarations`
- Ollama: OpenAI-compatible if using a tool-aware model

Built-in OpenAI `web_search_preview` is a special case: if a route needs web search and the target provider can't do it natively, either route to OpenAI or implement a standalone search tool.

## Usage / cost observability

`model_usage.py` writes one row per generation to a new table (`model_call_events`): provider, model, latency_ms, input_tokens, output_tokens, estimated_cost_usd, route_rule_matched, privacy_mode, success. Exposed via an admin endpoint.

## Configuration surface

New `.env` keys (placeholders only — never commit real values):

```
ANTHROPIC_API_KEY=
GEMINI_API_KEY=
OLLAMA_BASE_URL=http://localhost:11434
MODEL_ROUTER_CONFIG=config/router.yml
DEFAULT_PROVIDER=openai
```

## Phased delivery

1. **Phase 1:** Introduce `providers/base.py` and `providers/openai_provider.py`. `agent.py` routes everything to OpenAI. No behavior change. Tests confirm identical output.
2. **Phase 2:** Add Anthropic provider. Router config supports static default selection. `DEFAULT_PROVIDER` env var works.
3. **Phase 3:** Add rule-based router. Privacy-sensitive DMs can route to local (if Ollama is available) or to a smaller model.
4. **Phase 4:** Add fallback chain and usage logging.
5. **Phase 5:** Add Gemini and any remaining providers. PR the coherent slice upstream.

## Open questions

- Should `web_search` use OpenAI's built-in tool forever, or abstract it behind a standalone search integration? (Leaning: keep OpenAI built-in as Phase 1; add generic search tool in a later phase.)
- How should the router handle streaming? Upstream currently doesn't stream — leave non-streaming as Phase 1 and add streaming later.
- Should routing rules be YAML or Python? YAML is easier for non-devs to tune but harder to version-control semantically. Start with YAML.
