"""Celery application — task queue configuration.

Uses Redis as broker. Workers run as separate processes.
Workers may import from services/ but NEVER from api/.
"""

from __future__ import annotations

from celery import Celery

from app.config import get_settings


def create_celery_app() -> Celery:
    """Configure and return the Celery application."""
    settings = get_settings()

    celery_app = Celery(
        "ai_video_editor",
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend,
    )

    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,  # Fair scheduling for CPU-bound tasks
        worker_max_tasks_per_child=50,  # Recycle workers to prevent memory leaks
    )

    # Auto-discover tasks from workers package
    celery_app.autodiscover_tasks(["app.workers"])

    return celery_app


celery_app = create_celery_app()
