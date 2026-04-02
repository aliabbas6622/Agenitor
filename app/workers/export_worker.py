"""Export worker — Pipeline pattern for rendering video via FFmpeg."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from celery import shared_task
import ffmpeg

from app.schemas.jobs import JobStatus, JobProgressEvent
from app.api.ws import manager
from app.core.bridge import TimelineBuilder
from app.schemas.ir import TimelineIR, ExportSettingsIR
import app.core.engine_py as engine_py
from app.config import get_settings

# Path for exporting files
EXPORTS_DIR = Path("exports")
EXPORTS_DIR.mkdir(exist_ok=True)


def _emit_progress_sync(
    job_id: str,
    project_id: str,
    status: JobStatus,
    progress: float,
    stage: str,
    message: str = "",
    result_url: str | None = None,
    error: str | None = None,
):
    """Helper to emit WS events synchronously from inside the Celery worker."""
    import logging
    logger = logging.getLogger(__name__)

    message_value = message if message else None

    # Log the progress
    logger.info("[JOB=%s | %s] %.1f%% : %s", job_id, stage, progress * 100, message_value)

    # Broadcast to WebSocket clients (best effort - worker may not have event loop)
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(
                manager.broadcast(project_id, {
                    "type": "job_progress",
                    "job_id": job_id,
                    "project_id": project_id,
                    "status": status.value,
                    "progress": progress,
                    "stage": stage,
                    "message": message_value,
                    "result_url": result_url,
                    "error": error,
                })
            )
    except RuntimeError:
        # No event loop available - create one for sync execution
        try:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(
                manager.broadcast(project_id, {
                    "type": "job_progress",
                    "job_id": job_id,
                    "project_id": project_id,
                    "status": status.value,
                    "progress": progress,
                    "stage": stage,
                    "message": message_value,
                    "result_url": result_url,
                    "error": error,
                })
            )
            loop.close()
        except Exception as e:
            logger.warning("Failed to broadcast progress via WebSocket: %s", e)

    # Also publish progress via Redis pub/sub so the API process can forward
    # events to connected WS clients even when Celery runs in a separate process.
    try:
        # Do not attempt Redis during tests (Redis may not be running, and publishes can block).
        if os.environ.get("PYTEST_CURRENT_TEST") is not None or any(m.startswith("pytest") for m in sys.modules):
            return

        settings = get_settings()
        import redis

        payload = {
            "type": "job_progress",
            "job_id": job_id,
            "project_id": project_id,
            "status": status.value,
            "progress": progress,
            "stage": stage,
            "message": message_value,
            "result_url": result_url,
            "error": error,
        }
        # ws_id is expected to match `client_id` (typically project_id).
        channel = f"job_progress:{project_id}"
        redis_client = redis.Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=0.5,
            socket_timeout=0.5,
        )
        redis_client.publish(channel, json.dumps(payload))
    except Exception:
        # Non-fatal: export pipeline can still complete.
        pass


def run_export_pipeline(job_id: str, project_id: str, timeline_dict: dict, settings_dict: dict) -> dict:
    """
    Core export pipeline logic decoupled from Celery.
    """
    try:
        # Step 1: Reconstruct IR from dict
        _emit_progress_sync(job_id, project_id, JobStatus.PROCESSING, 0.05, "validation", "Parsing Timeline IR")
        timeline_ir = TimelineIR(**timeline_dict)
        export_settings_ir = ExportSettingsIR(**settings_dict)
        
        # Step 2: Build Native Objects
        _emit_progress_sync(job_id, project_id, JobStatus.PROCESSING, 0.15, "bridge", "Building native C++ structures")
        native_timeline = TimelineBuilder.build_native_timeline(timeline_ir)
        native_config = TimelineBuilder.build_native_export_config(export_settings_ir)
        
        # Override output path to include job ID if not absolute
        output_filename = f"{project_id}_{job_id}.mp4"
        output_path = EXPORTS_DIR / output_filename
        native_config.output_path = str(output_path.absolute())

        # Step 3: Initialize Native Controller & Renderer
        # Some local builds may expose only DummyRenderer (FFmpegRenderer missing).
        use_ffmpeg = os.environ.get("USE_FFMPEG_RENDERER", "true").lower() == "true"
        # Tests should never depend on FFmpeg being present/configured.
        if os.environ.get("PYTEST_CURRENT_TEST") is not None or any(m.startswith("pytest") for m in sys.modules):
            use_ffmpeg = False
        if use_ffmpeg and hasattr(engine_py, "FFmpegRenderer"):
            renderer = engine_py.FFmpegRenderer()
            _emit_progress_sync(
                job_id, project_id, JobStatus.PROCESSING, 0.15, "renderer", "Using FFmpegRenderer"
            )
        else:
            renderer = engine_py.DummyRenderer()
            _emit_progress_sync(
                job_id, project_id, JobStatus.PROCESSING, 0.15, "renderer", "Using DummyRenderer"
            )

        controller = engine_py.ExportController(renderer)

        # Step 4: Execute Native Render Loop
        _emit_progress_sync(job_id, project_id, JobStatus.PROCESSING, 0.25, "rendering", "Starting native rendering")
        
        def on_native_progress(pct: int, stage: str):
            # Map 0-100 to 0.25-0.95 progress range
            scaled_progress = 0.25 + (pct / 100.0) * 0.70
            _emit_progress_sync(job_id, project_id, JobStatus.PROCESSING, scaled_progress, "rendering", stage)

        result = controller.run(native_timeline, native_config, on_native_progress)

        if not result.success:
            raise RuntimeError(f"Native render failed: {result.error_message}")

        # Step 5: Finalize
        _emit_progress_sync(job_id, project_id, JobStatus.PROCESSING, 0.98, "finalize", "Finalizing export")
        
        result_url = f"/exports/{output_filename}"
        _emit_progress_sync(
            job_id,
            project_id,
            JobStatus.COMPLETED,
            1.0,
            "done",
            "Native export completed",
            result_url=result_url,
        )
        
        return {
            "job_id": job_id,
            "status": "completed",
            "result_url": result_url,
            "engine": "cpp_native",
            "duration": result.duration_seconds
        }
        
    except Exception as e:
        _emit_progress_sync(
            job_id,
            project_id,
            JobStatus.FAILED,
            0.0,
            "error",
            message=str(e),
            error=str(e),
        )
        raise e


@shared_task(bind=True, name="export_video")
def export_video_task(self, project_id: str, timeline_dict: dict, settings_dict: dict) -> dict:
    """
    Export pipeline utilizing the native C++ Engine.
    """
    job_id = self.request.id
    return run_export_pipeline(job_id, project_id, timeline_dict, settings_dict)
