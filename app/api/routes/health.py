from sqlalchemy import text
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends

from app.api.dependencies import settings_dependency
from app.core.config import Settings
from app.db.session import get_db
from app.schemas.admin import HealthResponse
from app.services.signal_gateway import SignalGateway

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dependency),
) -> HealthResponse:
    database = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        database = "degraded"
    signal_status = SignalGateway(settings).health()
    app_status = "ok" if database == "ok" and signal_status == "ok" else "degraded"
    return HealthResponse(status=app_status, signal_gateway=signal_status, database=database)
