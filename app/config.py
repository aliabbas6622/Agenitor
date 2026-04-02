"""Application configuration via environment variables."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration — loaded from .env or environment variables."""

    # ── App ───────────────────────────────────────────────
    app_env: str = "development"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_log_level: str = "info"

    # ── Database ──────────────────────────────────────────
    database_url: str = (
        "postgresql+asyncpg://editor:editor_secret@localhost:5432/ai_video_editor"
    )
    database_url_sync: str = (
        "postgresql+psycopg2://editor:editor_secret@localhost:5432/ai_video_editor"
    )

    # ── Redis ─────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── Celery ────────────────────────────────────────────
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # ── CORS ──────────────────────────────────────────────
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return json.loads(v)
        return v

    # ── AI Providers ──────────────────────────────────────
    openai_api_key: str | None = None
    elevenlabs_api_key: str | None = None
    
    # ── Asset Providers ───────────────────────────────────
    pexels_api_key: str | None = None
    pixabay_api_key: str | None = None

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    """Singleton settings accessor — cached after first call."""
    return Settings()
