# Local Setup Guide

## 1. Install Docker Desktop

1. Install Docker Desktop for Windows.
2. Start Docker Desktop.
3. Confirm the daemon is running.
4. Open a terminal and verify:

```powershell
docker --version
docker compose version
```

## 2. Prepare the project

1. Open the repository folder.
2. Copy `.env.example` to `.env`.
3. Fill in at minimum:

- `OPENAI_API_KEY`
- `DATABASE_URL`
- `SIGNAL_API_BASE_URL`
- `SIGNAL_BOT_NUMBER`
- `SIGNAL_WEBHOOK_SECRET`
- `ADMIN_API_TOKEN`
- `ADMIN_API_TOKENS` (optional, comma-separated)
- If you are not running the worker, set `INGESTION_WORKER_ENABLED=false` to use background tasks.
- To enable group auto-replies, set `ENABLE_GROUP_AUTO_REPLY=true` (optionally `GROUP_AUTO_REPLY_REQUIRE_QUESTION=true`).

## 3. Bootstrap the local stack

Run:

```powershell
make bootstrap
```

Expected outcome:

- Postgres container starts
- signal-cli-rest-api container starts
- Alembic migrations run

## 4. Launch the app

Run:

```powershell
make dev
```

Expected ports:

- `8000` for the FastAPI app
- `8080` for signal-cli-rest-api
- `5432` for Postgres
- ingestion worker runs as a background container

## 5. Register the laptop as the bot's primary Signal device

1. Obtain a fresh phone number for the bot account.
2. Start the compose stack.
3. Use the registration endpoint exposed by your installed `signal-cli-rest-api` version for `SIGNAL_BOT_NUMBER`.
4. Receive the Signal verification code by SMS or voice on that phone number.
5. Use the verification endpoint to complete account setup.
6. Confirm the bot account now exists on the laptop-hosted Signal stack.

Note:

- `signal-cli-rest-api` is unofficial.
- Register and verify endpoints can vary by image release.
- Keep the container image current.
- This repo assumes the laptop-hosted bot is the primary and only active Signal device for that account.

## 6. Send a group message

1. Add the newly registered bot account to a group.
2. Send a test message in that group.
3. Call:

```powershell
curl http://localhost:8000/health
```

4. Call:

```powershell
curl -H "Authorization: Bearer <ADMIN_API_TOKEN>" http://localhost:8000/admin/groups
```

Expected outcome:

- the group appears in admin output
- the message is stored
- the group is ready to be marked `authorized`, `ingest_only`, or `ignored`
- the laptop-hosted Signal account is confirmed to be receiving inbound traffic as the primary bot device

## 7. Mark group policy

Authorize a group:

```powershell
curl -X POST -H "Authorization: Bearer <ADMIN_API_TOKEN>" http://localhost:8000/admin/groups/<GROUP_ID>/authorize
```

Set ingest-only:

```powershell
curl -X POST -H "Authorization: Bearer <ADMIN_API_TOKEN>" http://localhost:8000/admin/groups/<GROUP_ID>/ingest-only
```

Ignore a group:

```powershell
curl -X POST -H "Authorization: Bearer <ADMIN_API_TOKEN>" http://localhost:8000/admin/groups/<GROUP_ID>/ignore
```

## 8. Verify authorized DM flow

1. Use a person who has posted recently in an `authorized` group.
2. Send a DM to the bot account.
3. The bot should answer privately.
4. The DM must not be embedded into shared group retrieval memory.

## 9. Verify unauthorized DM flow

1. Use a person only seen in an `ingest_only` group or never seen in an authorized group.
2. Send a DM to the bot account.
3. The bot should refuse politely.

## 10. Seed demo data if needed

Run:

```powershell
make ingest-demo
```

This creates:

- one authorized group
- one ingest-only group
- one allowed user
- one denied user

## 11. Run tests

Run:

```powershell
make test
```

Expected outcome:

- all unit, integration, and e2e tests pass
