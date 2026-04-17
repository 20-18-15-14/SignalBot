# Fork Purpose

## The Pathfinder Signal bot effort

Upstream (`CarmichaelAJ/SignalBot`) is a shared Pathfinder project. The owner posted an open call for contributors across five lanes:

1. Signal setup
2. **Model integration**
3. Hosting / DevOps
4. Data + Envision integration (manual pipeline)
5. Testing / QA

This fork (`20-18-15-14/SignalBot`) owns **Model Integration** primarily, with secondary involvement in Data/Envision work where the two overlap.

## What "Model Integration" covers here

- Provider abstraction: a single interface the bot calls, pluggable providers behind it.
- Provider implementations: Anthropic (Claude), OpenAI, Google Gemini, local via Ollama.
- Routing: picking the right provider per message based on attributes (sensitivity, length, tool needs, cost).
- Fallback: graceful degradation when primary fails.
- Tool calling: normalized across providers so prompts don't care about provider-specific schemas.
- Cost / latency / usage observability per provider.

## What this fork does NOT own

- Signal transport or webhook normalization — that's upstream and stable.
- Retrieval logic (pgvector, chunking, scoring) — that's upstream.
- Envision ingestion pipelines — adjacent lane, coordinate don't duplicate.
- Hosting / DevOps — another lane.

## Contribution path

Work here starts as experimentation in this fork. When a feature slice is coherent, tested, and aligns with upstream architecture, it is PR'd back to `CarmichaelAJ/SignalBot`. Upstream may accept, request changes, or decline. Either way, this fork continues to run as a complete implementation.

## Why a fork and not a parallel sidecar service

Tradeoff considered: a standalone router service with a single `/generate` endpoint would keep the fork zero-touch. Rejected because:

- The multi-model work is genuinely inside the bot's generation path — the abstraction belongs in `app/services/`, not across a network boundary.
- A sidecar doubles deployment complexity for the upstream team to adopt.
- Forking makes contribution path explicit and keeps architectural cohesion.

## Non-goals

- Don't introduce an opinionated agent framework (LangChain, LlamaIndex, etc.). Keep the abstraction thin and swappable.
- Don't break the upstream default path. OpenAI must remain a supported provider and can be the default.
- Don't move secrets outside `.env` — secret rotation is a DevOps lane concern.
