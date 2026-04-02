"""FastAPI application factory."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import sys

from app.config import get_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup / shutdown lifecycle hooks."""
    # ── Startup ───────────────────────────────────────────
    settings = get_settings()
    logger.info("AI Video Editor starting in %s mode", settings.app_env)

    # Start Redis pub/sub bridge for job progress delivery (Celery worker -> WS).
    # Tests and dev environments without Redis should not fail startup.
    if os.environ.get("PYTEST_CURRENT_TEST") is None and not any(m.startswith("pytest") for m in sys.modules):
        try:
            from app.api.ws import manager as ws_manager

            await ws_manager.start_redis_progress_bridge(settings.redis_url)
        except Exception:
            logger.warning("Redis progress bridge not started (non-fatal).", exc_info=True)
    yield
    # ── Shutdown ──────────────────────────────────────────
    logger.info("AI Video Editor shutting down")


def create_app() -> FastAPI:
    """Build and configure the FastAPI instance."""
    settings = get_settings()

    app = FastAPI(
        title="AI-Native Video Editor",
        description="Backend orchestration engine for AI-driven video production",
        version="0.1.0",
        lifespan=lifespan,
        debug=settings.app_debug,
    )

    # ── CORS ──────────────────────────────────────────────
    # SECURITY: Restrict methods and headers in production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

    # ── Routers ───────────────────────────────────────────
    from app.api.routes.health import router as health_router
    from app.api.routes.jobs import router as jobs_router
    from app.api.routes.preview import router as preview_router
    from app.api.routes.projects import router as projects_router
    from app.api.routes.timeline import router as timeline_router
    from app.api.routes.ai import router as ai_router
    from app.api.routes.assets import router as assets_router

    # ── Static files (exports) ────────────────────────────
    # Export worker writes into `<repo_root>/exports/`. Expose it so clients can download results.
    from pathlib import Path

    exports_dir = Path(__file__).resolve().parent.parent / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/exports", StaticFiles(directory=str(exports_dir)), name="exports")

    app.include_router(health_router)
    app.include_router(projects_router)
    app.include_router(timeline_router)
    app.include_router(jobs_router)
    app.include_router(ai_router)
    app.include_router(preview_router)
    app.include_router(assets_router)

    return app


# Module-level app for `uvicorn app.main:app`
app = create_app()
