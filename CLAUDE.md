# CLAUDE.md

Project context for Claude Code sessions working in this fork.

## What this is

Fork of `CarmichaelAJ/SignalBot` owned by `20-18-15-14` (Shaun Pettis, Pathfinder). The upstream project is a Signal-connected OSINT assistant (FastAPI + Postgres/pgvector + signal-cli-rest-api) shared across Pathfinder channels.

Upstream README: https://github.com/CarmichaelAJ/SignalBot

## Why this fork exists

This fork owns the **Model Integration** lane for the Pathfinder Signal bot effort. See `docs/FORK_PURPOSE.md`.

Upstream currently hardcodes OpenAI Responses API in `app/services/agent.py`. This fork introduces a provider-agnostic abstraction so the bot can route across Anthropic, OpenAI, Gemini, and local models.

## Working in this fork

- `main` tracks upstream. Do not commit feature work directly to `main`.
- Feature work lives on branches (`feature/<slug>`). See `docs/BRANCHING.md`.
- Sync with upstream regularly: `git fetch upstream && git merge upstream/main`.
- PRs back to upstream are opened when a feature slice is coherent and tested.

## Architecture constraints to respect

The upstream architecture (see `ARCHITECTURE.md`) has principles you must preserve:

- **DMs are private** — direct message content never enters shared retrieval memory.
- **DM authorization** is gated by observed membership in an `authorized` group.
- **Group auto-replies** are disabled by default.
- **Retrieval before generation** — always prefer local context over web search.
- **Transport health** (`signal_gateway`) is independent of app health.

Any change that weakens these guarantees is out of scope.

## The integration seam

`app/services/agent.py::AgentService.answer()` is the single entry point from the orchestrator to the model. Contract:

```
Input:  question, group_context, knowledge_context, authorized_group_ids, privacy_mode
Output: {text: str, sources: list[dict], usage: dict}
```

Multi-model work replaces the body of `answer()` (and `build_input()`) with a provider abstraction. The contract stays stable so `orchestrator.py` and `routes/webhooks.py` never need to know which model responded.

Design details: `docs/MULTI_MODEL_DESIGN.md`.

## Dev environment

- Python 3.12
- `uv` for package management (inside container)
- Docker Compose for local run (`docker compose up`)
- Postgres + pgvector for retrieval
- See `LOCAL_SETUP.md` for the upstream-provided setup steps

## Secrets

- `.env` is gitignored. Copy from `.env.example`.
- Never commit API keys. When adding new providers, extend `.env.example` with placeholders only.
- When suggesting an API key in chat, reference it by env var name, not value.

## Code conventions

- Match the existing style in `app/` — type hints, small classes, explicit dependency injection via `Settings`.
- Tests live under `tests/` and use pytest.
- Migrations via Alembic under `migrations/`.
- New providers go under `app/services/providers/` (new module — create when needed).

## What to do when stuck

- Read `ARCHITECTURE.md` before proposing architectural changes.
- Read `docs/FORK_PURPOSE.md` before scoping new features — some things belong upstream, some belong here.
- If you are unsure whether a change should live in this fork or go upstream, ask.
