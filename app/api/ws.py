"""WebSocket connection manager for real-time progress events."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Dict, List

from fastapi import WebSocket
import redis.asyncio as redis_async


class ConnectionManager:
    """Manages WebSocket connections and broadcasts events."""

    def __init__(self):
        # Map connection ID (or user ID, or project ID) to active websockets
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, ws_id: str, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            if ws_id not in self.active_connections:
                self.active_connections[ws_id] = []
            self.active_connections[ws_id].append(websocket)

    async def disconnect(self, ws_id: str, websocket: WebSocket):
        async with self._lock:
            if ws_id in self.active_connections:
                if websocket in self.active_connections[ws_id]:
                    self.active_connections[ws_id].remove(websocket)
                if not self.active_connections[ws_id]:
                    del self.active_connections[ws_id]

    async def broadcast(self, ws_id: str, message: dict):
        """Send a JSON message to all clients listening to a specific ID (like project_id)."""
        async with self._lock:
            connections = self.active_connections.get(ws_id, [])
            
        for connection in list(connections):
            try:
                await connection.send_json(message)
            except Exception:
                # Connection might be dead
                await self.disconnect(ws_id, connection)

    async def start_redis_progress_bridge(self, redis_url: str) -> None:
        """Forward job progress from Celery workers to WS clients via Redis pub/sub.

        Celery workers and the API typically run as different processes. Without this,
        the in-memory WS manager cannot receive events published from workers.
        """
        if os.environ.get("PYTEST_CURRENT_TEST") is not None or any(m.startswith("pytest") for m in sys.modules):
            return

        # Avoid starting twice.
        if getattr(self, "_redis_bridge_task", None) is not None:
            return

        async def _run() -> None:
            try:
                redis_client = redis_async.Redis.from_url(redis_url, decode_responses=True)
                pubsub = redis_client.pubsub()
                await pubsub.psubscribe("job_progress:*")
                async for msg in pubsub.listen():
                    if not msg:
                        continue
                    if msg.get("type") != "pmessage":
                        continue
                    channel = msg.get("channel", "")
                    data = msg.get("data")
                    # channel looks like: "job_progress:<ws_id>"
                    ws_id = str(channel).split(":", 1)[1] if ":" in str(channel) else ""
                    if not ws_id:
                        continue
                    if isinstance(data, str):
                        try:
                            payload = json.loads(data)
                        except json.JSONDecodeError:
                            continue
                    else:
                        payload = data
                    # Best-effort: drop messages if WS layer is misconfigured.
                    try:
                        await self.broadcast(ws_id, payload)
                    except Exception:
                        continue
            except Exception:
                # Redis may not be available (dev/test). WS remains functional for in-process broadcasts.
                return

        self._redis_bridge_task = asyncio.create_task(_run())


# Global instance
manager = ConnectionManager()
