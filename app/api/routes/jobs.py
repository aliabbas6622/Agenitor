"""Export jobs API — submit render jobs and stream progress via WebSockets."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.ws import manager
from app.schemas.jobs import JobRequest
from app.workers.export_worker import export_video_task

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


@router.post("/export", status_code=202)
async def start_export(request: JobRequest):
    """Start an asynchronous video export job."""
    
    # Normally we would fetch the timeline from DB based on project_id, 
    # but request.timeline is provided here for easy payload testing.
    task = export_video_task.delay(
        project_id=str(request.project_id),
        timeline_dict=request.timeline.model_dump(mode="json"),
        settings_dict=request.export_settings.model_dump(mode="json"),
    )
    
    return {
        "job_id": task.id,
        "project_id": request.project_id,
        "status": "pending",
        "message": "Export job queued via Celery."
    }


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint to stay connected for job progress events."""
    await manager.connect(client_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # We can handle incoming WS messages here if needed, 
            # e.g., acknowledging progress updates.
            await manager.broadcast(client_id, {"type": "ack", "message": f"Received: {data}"})
    except WebSocketDisconnect:
        await manager.disconnect(client_id, websocket)
