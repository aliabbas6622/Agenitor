"""Health check endpoints for infrastructure monitoring."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import get_settings

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    status: str
    environment: str
    version: str


class ComponentHealth(BaseModel):
    status: str
    detail: str = ""


class DetailedHealthResponse(BaseModel):
    status: str
    database: ComponentHealth
    redis: ComponentHealth
    celery: ComponentHealth


@router.get("", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic health check — confirms the API is running."""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        environment=settings.app_env,
        version="0.1.0",
    )


@router.get("/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check() -> DetailedHealthResponse:
    """Detailed health check — probes database, Redis, and Celery."""
    db_status = ComponentHealth(status="ok", detail="placeholder — wired in Phase 2")
    redis_status = ComponentHealth(status="ok", detail="placeholder — wired in Phase 2")
    celery_status = ComponentHealth(status="ok", detail="placeholder — wired in Phase 3")

    overall = "ok"
    for component in [db_status, redis_status, celery_status]:
        if component.status != "ok":
            overall = "degraded"
            break

    return DetailedHealthResponse(
        status=overall,
        database=db_status,
        redis=redis_status,
        celery=celery_status,
    )
