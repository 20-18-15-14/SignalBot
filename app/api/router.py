from fastapi import APIRouter

from app.api.routes.admin import router as admin_router
from app.api.routes.health import router as health_router
from app.api.routes.webhooks import router as webhook_router

router = APIRouter()
router.include_router(health_router)
router.include_router(admin_router)
router.include_router(webhook_router)
