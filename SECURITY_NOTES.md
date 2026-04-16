# Security Notes

## Intended Privacy Posture

- Group chats are shared memory only within approved retrieval scopes.
- Direct messages are private by default.
- Direct-message content is never embedded into shared retrieval memory.
- Direct-message storage is minimal and configurable.

## MVP Safeguards

- Webhook secret validation.
- Admin bearer-token auth.
- Group-scoped retrieval boundaries.
- Best-effort authorization checks before DM replies.
- No auto-replies in groups by default.

## Hardening Before VPS Deployment

1. Put the API behind TLS and authenticated reverse proxying.
2. Restrict admin routes to a trusted network boundary.
3. Replace static admin token auth with stronger identity.
4. Encrypt backups and Postgres volumes.
5. Add secret scanning and log redaction.
