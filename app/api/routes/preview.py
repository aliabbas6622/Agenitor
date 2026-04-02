"""Preview endpoints — real-time frame streaming for timeline scrubbing."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.api.ws import manager
from app.schemas.ir import TimelineIR
from app.services.preview_service import get_preview_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/preview", tags=["preview"])


@router.websocket("/ws")
async def preview_websocket(
    websocket: WebSocket,
    project_id: Annotated[str, Query()],
):
    """
    WebSocket endpoint for real-time preview frame streaming.

    Clients connect with their project ID and send timestamp requests.
    Server responds with base64-encoded frames for each timestamp.

    Client -> Server: {"timestamp": 1.5, "timeline": {...}}
    Server -> Client: {"frame_b64": "...", "timestamp": 1.5, "width": 640, "height": 360}
    """
    await websocket.accept()
    await manager.connect(project_id, websocket)

    preview_svc = get_preview_service()

    try:
        while True:
            data = await websocket.receive_json()

            timestamp = data.get("timestamp", 0.0)
            timeline_data = data.get("timeline")
            width = data.get("width", 640)
            height = data.get("height", 360)

            if not timeline_data:
                await websocket.send_json({
                    "type": "error",
                    "message": "Timeline data required",
                })
                continue

            try:
                # Parse timeline from JSON
                timeline = TimelineIR(**timeline_data)

                # Extract frame
                frame_result = preview_svc.grab_frame(
                    timeline,
                    timestamp,
                    width=width,
                    height=height,
                )

                # Send frame back to client
                await websocket.send_json({
                    "type": "frame",
                    **frame_result,
                })

            except Exception as e:
                logger.exception("Error processing frame request")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e),
                })

    except WebSocketDisconnect:
        await manager.disconnect(project_id, websocket)
        logger.info("Preview client disconnected: %s", project_id)


@router.post("/frame")
async def grab_single_frame(
    timeline: TimelineIR,
    timestamp: float = Query(..., ge=0.0, description="Timestamp in seconds"),
    width: int = Query(640, ge=128, le=1920),
    height: int = Query(360, ge=72, le=1080),
):
    """
    REST endpoint for grabbing a single preview frame.

    Useful for clients that don't want to maintain a WebSocket connection.
    Slower than WebSocket for repeated requests.
    """
    preview_svc = get_preview_service()
    result = preview_svc.grab_frame(timeline, timestamp, width, height)
    return result
