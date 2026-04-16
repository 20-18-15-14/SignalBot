# Architecture

## Services and Modules

### `signal_gateway`

- Wraps `signal-cli-rest-api`.
- Normalizes inbound webhook payloads to `NormalizedSignalMessage`.
- Sends outbound DM or group messages.
- Tracks transport health independently from the rest of the app.
- Assumes the bot account is registered directly on the laptop-hosted Signal stack as a primary device.

### `policy_engine`

- Decides ingestion and response behavior.
- Group messages are ingested unless the group is `ignored`.
- Direct messages are never added to shared retrieval memory.
- Direct messages only receive replies when the sender has recent membership evidence in at least one `authorized` group.
- Group auto-replies are disabled by default.

### `memory`

- Stores raw group messages.
- Stores minimal DM operational logs when enabled.
- Builds conversation-aware chunks from grouped messages instead of embedding single tiny messages.
- Retrieves only from allowed groups and optional filters.
- Uses native pgvector similarity search in PostgreSQL for production retrieval.
- Uses an ingestion job queue and worker to handle reindexing and deferred chunking.

### `knowledge_ingest`

- Ingests admin-managed local files.
- Supports `.txt` and `.md`.
- Accepts `.pdf` as a documented stub path for the MVP.
- Supports `global`, `group`, and `admin_only` collections.

### `agent`

- Calls OpenAI Responses API.
- Injects system instructions plus retrieved group and knowledge context.
- Uses OpenAI built-in `web_search` tool when enabled.
- Returns source-aware payloads and token-usage metadata.

### `ingestion_worker`

- Claims pending ingestion jobs.
- Handles reindex and group ingestion in the background.

## Data Separation

- Group chats are shared memory only within approved scopes.
- Direct messages are private and are never embedded into shared retrieval memory.
- Knowledge collections stay separate from chat-derived memory.
- SQLite remains a test-only fallback for embeddings; PostgreSQL is the intended retrieval backend.

## Signal Account Model

- The bot uses a dedicated Signal account and number.
- The laptop-hosted `signal-cli-rest-api` stack is the primary and only active device for that account.
- Registration happens through `signal-cli-rest-api` register and verify endpoints rather than QR linking.
- This is practical for future VPS migration, but it relies on unofficial tooling and should be monitored for breakage across Signal or signal-cli changes.

## Request Flows

### Group message

1. Signal webhook arrives.
2. Payload is normalized.
3. Policy allows ingestion unless the group is `ignored`.
4. Raw message is stored and membership evidence is updated.
5. Background ingestion builds conversation chunks.
6. No reply is sent by default.

### Authorized DM

1. Direct message arrives.
2. Membership evidence is checked against `authorized` groups.
3. Group-scoped memory and knowledge are retrieved.
4. OpenAI Responses API generates an answer and may use web search.
5. Reply is sent privately.
6. DM content is not added to shared memory.

### Unauthorized DM

1. Direct message arrives.
2. No authorized-group eligibility is found.
3. Bot sends a polite refusal.
