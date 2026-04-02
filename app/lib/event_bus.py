"""Async Event Bus — Observer pattern for cross-module communication.

Events are named <entity>:<past-tense-verb> (e.g. clip:trimmed, export:completed).
Listeners are independent — one listener's failure does not block others.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)

# Handler type: async function taking event data kwargs
EventHandler = Callable[..., Coroutine[Any, Any, None]]


class EventBus:
    """Lightweight async event bus for domain events.

    Usage:
        bus = EventBus()

        @bus.on("clip:trimmed")
        async def handle_trim(clip_id: str, new_duration: float):
            await auto_save(clip_id)

        await bus.emit("clip:trimmed", clip_id="abc", new_duration=5.0)
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def on(self, event_name: str) -> Callable[[EventHandler], EventHandler]:
        """Decorator to register an event handler."""
        def decorator(handler: EventHandler) -> EventHandler:
            self._handlers[event_name].append(handler)
            return handler
        return decorator

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        """Programmatic subscription."""
        self._handlers[event_name].append(handler)

    def unsubscribe(self, event_name: str, handler: EventHandler) -> None:
        """Remove a handler."""
        self._handlers[event_name] = [
            h for h in self._handlers[event_name] if h != handler
        ]

    async def emit(self, event_name: str, **kwargs: Any) -> None:
        """Fire an event — runs all handlers concurrently.

        Individual handler failures are logged but do not propagate.
        """
        handlers = self._handlers.get(event_name, [])
        if not handlers:
            return

        results = await asyncio.gather(
            *(h(**kwargs) for h in handlers),
            return_exceptions=True,
        )
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "Event handler %s for '%s' failed: %s",
                    handlers[i].__name__,
                    event_name,
                    result,
                )

    @property
    def registered_events(self) -> list[str]:
        """List all event names with registered handlers."""
        return list(self._handlers.keys())


# Global event bus instance
event_bus = EventBus()
