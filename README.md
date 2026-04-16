# signal-osint-agent

`signal-osint-agent` is a production-minded local MVP for a Signal-connected assistant that ingests approved group chat traffic, answers authorized direct messages privately, and combines group memory, local knowledge files, OpenAI Responses API generation, and OpenAI built-in web search.

## Proposed Repository Tree

```text
signal-osint-agent/
├── app/
│   ├── api/
│   ├── core/
│   ├── db/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── cli.py
│   └── main.py
├── knowledge/
├── migrations/
├── scripts/
├── tests/
├── .env.example
├── alembic.ini
├── ARCHITECTURE.md
├── docker-compose.yml
├── Dockerfile
├── Makefile
├── README.md
├── RUNBOOK.md
├── SECURITY_NOTES.md
└── pyproject.toml
```

## What This MVP Does

1. Accepts Signal webhook payloads and normalizes them into internal message objects.
2. Stores and ingests group chat messages into PostgreSQL-backed memory.
3. Maintains best-effort membership observations from observed group traffic.
4. Allows direct-message responses only for users seen in at least one `authorized` group.
5. Refuses unauthorized DMs politely.
6. Keeps direct-message content out of shared retrieval memory.
7. Supports local knowledge ingestion for `.txt`, `.md`, and `.pdf`.
8. Queues ingestion jobs and processes them via a background worker.
9. Optionally auto-replies in authorized groups when enabled, with rate limits.
10. Uses OpenAI Responses API for answer generation and built-in `web_search` when enabled.

## Stack

- Python 3.12
- FastAPI
- uv package workflow inside the image
- PostgreSQL
- pgvector image for Postgres initialization
- SQLAlchemy + Alembic
- pytest
- Docker Compose
- signal-cli-rest-api

## Quick Start

### 1. Install prerequisites

Install Docker Desktop on the laptop and confirm both `docker` and `docker compose` work.

Install Python 3.12 locally if you want to run tests or scripts outside containers.

### 2. Configure environment

Copy `.env.example` to `.env` and fill in:

- `OPENAI_API_KEY`
- `DATABASE_URL`
- `SIGNAL_API_BASE_URL`
- `SIGNAL_BOT_NUMBER`
- `SIGNAL_WEBHOOK_SECRET`
- `ADMIN_API_TOKEN`
- `ADMIN_API_TOKENS` (optional, comma-separated)
- If you are not running the worker, set `INGESTION_WORKER_ENABLED=false` to use background tasks.
- To enable group auto-replies, set `ENABLE_GROUP_AUTO_REPLY=true` (optionally `GROUP_AUTO_REPLY_REQUIRE_QUESTION=true`).

### 3. Bootstrap dependencies

Run:

```bash
make bootstrap
```

This script checks Docker, validates required env vars, starts Postgres and `signal-cli-rest-api`, waits briefly, runs Alembic migrations, and prints next steps.

### 4. Start the stack

Run:

```bash
make dev
```

This starts the API and the ingestion worker containers.

### 5. Register the laptop-hosted Signal account as the primary device

This deployment assumes the bot gets a brand-new Signal account whose only active device is the laptop-hosted `signal-cli-rest-api` stack.

You still need a phone number that can receive the Signal verification code, but you do not need to keep a phone logged in as the primary Signal client after registration.

Recommended operator flow:

1. Obtain a fresh phone number for the bot account.
2. Start the Compose stack so `signal-cli-rest-api` is reachable on `http://localhost:8080`.
3. Use the registration endpoints exposed by your installed `signal-cli-rest-api` version to start primary-device registration for `SIGNAL_BOT_NUMBER`.
4. Receive the verification code by SMS or voice on that phone number.
5. Submit the verification code through the REST API to complete account registration.
6. Confirm the account is now registered on the laptop-hosted Signal stack.

Typical `signal-cli-rest-api` flows expose endpoints in this family:

- `POST /v1/register/{number}`
- `POST /v1/register/{number}/verify/{code}`
- account/status helpers under `/v1/accounts` or similar

The exact paths can vary by image release, so verify them against the version of `bbernhard/signal-cli-rest-api` you are running.

Important:

- This primary-device automation path is based on unofficial tooling.
- Keeping `signal-cli-rest-api` current matters.
- Future Signal changes can require transport maintenance.
- A fresh bot number is strongly preferred over reusing a personal Signal account.

### 6. Send a test group message

After registration, use the newly registered bot account on the laptop-hosted stack, add it to a group, send a message, and check:

```bash
curl -H "Authorization: Bearer $ADMIN_API_TOKEN" http://localhost:8000/admin/groups
```

### 7. Authorize one group

```bash
curl -X POST -H "Authorization: Bearer $ADMIN_API_TOKEN" \
  http://localhost:8000/admin/groups/<group_id>/authorize
```

### 8. Verify ingestion

```bash
curl http://localhost:8000/health
```

```bash
curl -H "Authorization: Bearer $ADMIN_API_TOKEN" \
  http://localhost:8000/admin/ingestion/health
```

### 9. Send an authorized DM

If the sender has recent membership observations in an `authorized` group, the bot retrieves allowed group memory plus knowledge, optionally uses web search, and replies privately.

### 10. Try an unauthorized DM

If the sender is only in `ingest_only` groups or is unseen, the bot sends a polite refusal and does not ingest the DM into shared memory.

## Admin API

- `GET /health`
- `GET /admin/groups`
- `POST /admin/groups/{group_id}/authorize`
- `POST /admin/groups/{group_id}/ingest-only`
- `POST /admin/groups/{group_id}/ignore`
- `POST /admin/reindex`
- `POST /admin/knowledge/upload`
- `GET /admin/users/{user_id}/access`
- `GET /admin/ingestion/health`
- `POST /webhooks/signal`

## CLI

```bash
python -m app.cli init-db
python -m app.cli reembed <group_id>
python -m app.cli add-knowledge ./knowledge/example.md --collection-scope global
```

## Demo Seed

```bash
make ingest-demo
```

This seeds two groups, one `authorized`, one `ingest_only`, one allowed user, and one denied user.

## Testing

```bash
make test
```

## Notes on pgvector

The Compose database image includes pgvector and the Alembic migration initializes the extension. Production retrieval now uses native `pgvector` columns plus cosine-distance ordering in PostgreSQL. The SQLite test path still falls back to JSON-backed embeddings and application-side scoring so the test suite can run without Postgres.

## Signal Deployment Note

This repo now assumes a laptop-hosted primary Signal account for the bot, not a linked secondary desktop. The laptop/container stack is the bot's only active Signal device. That is operationally convenient for later VPS migration, but it depends on unofficial tooling and should be treated as a maintenance-sensitive integration.
# SignalBot
