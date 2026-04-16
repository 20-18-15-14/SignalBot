# Runbook

## Normal Startup

1. Confirm `.env` is present and populated.
2. Run `make bootstrap`.
3. Register the bot's Signal account on the laptop-hosted stack if it is not already registered.
4. Run `make dev` (this starts the API and ingestion worker).
5. Check `GET /health`.

If you are running the API without Compose, start the worker separately:

```bash
python -m app.workers.ingestion_worker
```

## Primary Account Registration

This deployment uses the laptop-hosted `signal-cli-rest-api` stack as the bot's primary and only Signal device.

1. Obtain a fresh phone number for the bot.
2. Start `signal-cli-rest-api`.
3. Call the registration endpoint for `SIGNAL_BOT_NUMBER`.
4. Receive the SMS or voice verification code for that number.
5. Call the verification endpoint to complete registration.
6. Confirm the account exists in the REST API account/status view.

Because the REST API wrapper can change endpoint details across versions, verify the exact register/verify/status routes against the image version you are running.

## Common Checks

### App health

```bash
curl http://localhost:8000/health
```

### List groups

```bash
curl -H "Authorization: Bearer $ADMIN_API_TOKEN" \
  http://localhost:8000/admin/groups
```

### Inspect user DM eligibility

```bash
curl -H "Authorization: Bearer $ADMIN_API_TOKEN" \
  http://localhost:8000/admin/users/<user_id>/access
```

### Reindex stored group memory

```bash
python -m app.cli reembed <group_id>
```

### Reindex with the ingestion worker

```bash
curl -X POST -H "Authorization: Bearer $ADMIN_API_TOKEN" \
  http://localhost:8000/admin/reindex
```

## Troubleshooting

- Group messages missing: check webhook secret, app logs, and group state.
- DMs denied unexpectedly: inspect `/admin/users/{user_id}/access` and confirm recent membership evidence in an `authorized` group.
- OpenAI failures: verify `OPENAI_API_KEY`, outbound network access, and model availability.
- signal-cli-rest-api unhealthy: inspect container logs and confirm the bot number is still registered on the laptop-hosted stack.
- registration fails: verify the phone number can receive SMS or voice verification and that the REST API version still exposes the expected register/verify endpoints.
