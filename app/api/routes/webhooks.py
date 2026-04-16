from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException

from app.api.dependencies import orchestrator_dependency, settings_dependency
from app.core.config import Settings
from app.services.orchestrator import InboundMessageOrchestrator
from app.services.signal_gateway import SignalGateway

router = APIRouter(tags=["signal"])


@router.post("/webhooks/signal")
def signal_webhook(
    payload: dict,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(settings_dependency),
    orchestrator: InboundMessageOrchestrator = Depends(orchestrator_dependency),
    x_signal_secret: str | None = Header(default=None),
) -> dict:
    if not settings.signal_webhook_secret:
        raise HTTPException(status_code=500, detail="webhook secret is not configured")
    if x_signal_secret != settings.signal_webhook_secret:
        raise HTTPException(status_code=401, detail="invalid webhook secret")
    normalized = SignalGateway(settings).normalize_event(payload)
    result = orchestrator.handle(normalized, background_tasks=background_tasks)
    orchestrator.repository.db.commit()
    return result
