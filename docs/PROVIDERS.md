# Adding a Provider

How to plug a new LLM provider (Anthropic, Gemini, Vertex AI, Ollama, etc.) into this fork.

## The contract

A provider implements `LLMProvider` (see `app/services/providers/base.py`):

```python
class LLMProvider(Protocol):
    name: str
    def generate(self, request: GenerationRequest) -> GenerationResponse: ...
```

`GenerationRequest` carries the question, context blobs from retrieval, authorized group IDs, a privacy flag, and a `web_search_enabled` hint. Each provider decides how (or whether) to honor the hint — for example, OpenAI uses its built-in `web_search_preview` tool; providers without native web search can ignore the flag or implement a generic search tool later.

`GenerationResponse` returns `text`, `usage` (freeform dict, normalize when feasible), and a `provider` name string.

## Steps

1. **Create the module.** Add `app/services/providers/<name>_provider.py`. Implement the class, set `name = "<slug>"`.

2. **Register it.** In `app/services/providers/__init__.py`, add a line to `PROVIDERS`:

   ```python
   PROVIDERS: dict[str, ProviderFactory] = {
       "openai": lambda s: OpenAIProvider(s),
       "vertex": lambda s: VertexProvider(s),   # <— your addition
       "stub": lambda _: StubProvider(),
   }
   ```

3. **Extend `Settings`** in `app/core/config.py` with any provider-specific config (API keys, project IDs, regions, timeouts). Use sensible defaults so the default `OPENAI`-based path still boots with an empty `.env`.

4. **Extend `.env.example`** with placeholder values only. Never commit real keys.

5. **Select it.** Set `DEFAULT_PROVIDER=<slug>` in `.env` or pass an explicit provider to `AgentService(settings, provider=...)` in tests.

6. **Add tests** in `tests/unit/test_providers.py` or a sibling file. Use the existing `_RecordingProvider` pattern as a reference for mocking.

## GCP / Vertex AI notes

Vertex AI supports several model families through one platform: Gemini (native), Anthropic Claude (via the Anthropic partnership), and open/custom models via Model Garden. Design hints:

- **Auth:** Vertex expects Application Default Credentials (ADC) or a service-account JSON, a GCP project ID, and a region. Add `VERTEX_PROJECT`, `VERTEX_REGION`, and `GOOGLE_APPLICATION_CREDENTIALS` to `Settings` and `.env.example`. Do not commit credential paths that are laptop-specific.
- **Split or unified?** You can either ship a single `VertexProvider` that routes to Gemini/Claude/etc. based on a model slug, or separate `VertexGeminiProvider` and `VertexAnthropicProvider`. The latter is cleaner for routing rules but duplicates some plumbing. Start unified; split later if routing needs it.
- **SDKs:** `google-cloud-aiplatform`, `google-genai`, or `anthropic[vertex]` depending on the model. Pin versions in `pyproject.toml`.
- **Tool calling:** Gemini uses `function_declarations`; Anthropic-on-Vertex follows the Anthropic Messages API schema. Normalize at the provider boundary. The generic `web_search_enabled` flag can be mapped to a custom search tool if Vertex doesn't offer a native equivalent.
- **Regions matter.** Anthropic models on Vertex are gated to specific regions (e.g., `us-east5`). Fail loudly if a region/model combo isn't supported rather than silently falling back.

## What the fork maintainer will and won't accept

- **Will accept:** clean provider implementations that follow the contract, tests, docs entries.
- **Will not accept:** agent framework dependencies (LangChain, LlamaIndex, etc.); changes that break the OpenAI default path; secrets committed to `.env.example`; changes to the `AgentService.answer()` return shape.

If in doubt about scope, open a draft PR early for discussion.
