from fastapi import FastAPI

import os

from app.api.router import router
from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(title="signal-osint-agent", version="0.1.0")
app.include_router(router)


@app.on_event("startup")
def validate_runtime_settings() -> None:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return
    if not settings.signal_webhook_secret:
        raise RuntimeError("SIGNAL_WEBHOOK_SECRET must be set for the API to start.")
    if not settings.admin_token_list():
        raise RuntimeError("ADMIN_API_TOKEN or ADMIN_API_TOKENS must be set for the API to start.")
