"""Preview service — frame extraction for real-time timeline preview."""

from __future__ import annotations

import base64
import logging
from typing import TYPE_CHECKING

from app.core.bridge import TimelineBuilder
from app.schemas.ir import TimelineIR

if TYPE_CHECKING:
    import app.core.engine_py as engine_py

logger = logging.getLogger(__name__)


class PreviewService:
    """Service for extracting preview frames from timeline."""

    def __init__(self):
        self._frame_grabber: "engine_py.FrameGrabber | None" = None

    def _get_grabber(self) -> "engine_py.FrameGrabber":
        """Lazy-initialize the frame grabber."""
        if self._frame_grabber is None:
            import app.core.engine_py as engine_py
            self._frame_grabber = engine_py.FrameGrabber()
        return self._frame_grabber

    def grab_frame(
        self,
        timeline: TimelineIR,
        timestamp: float,
        width: int = 640,
        height: int = 360,
    ) -> dict:
        """
        Extract a single frame from the timeline at the specified timestamp.

        Args:
            timeline: The timeline to extract from
            timestamp: Time in seconds to extract frame at
            width: Output frame width (default 640)
            height: Output frame height (default 360)

        Returns:
            dict with keys:
                - frame_b64: Base64-encoded JPEG frame
                - timestamp: The timestamp that was extracted
                - width: Frame width
                - height: Frame height
                - valid: Whether a valid frame was extracted
        """
        try:
            # Convert Pydantic IR to C++ native
            native_timeline = TimelineBuilder.build_native_timeline(timeline)

            # Grab frame from C++ engine
            grabber = self._get_grabber()
            frame_data = grabber.grab_frame(native_timeline, timestamp, width, height)

            if not frame_data.valid:
                logger.warning("Frame grab returned invalid result at t=%.2f", timestamp)

            # Convert RGB bytes to base64-encoded JPEG for transport
            # For simplicity, we'll send raw RGB data as base64
            # A production implementation would encode as JPEG
            frame_b64 = base64.b64encode(frame_data.to_bytes()).decode("ascii")

            return {
                "frame_b64": frame_b64,
                "timestamp": timestamp,
                "width": frame_data.width,
                "height": frame_data.height,
                "valid": frame_data.valid,
            }

        except Exception as e:
            logger.error("Failed to grab frame at t=%.2f: %s", timestamp, e)
            # Return a blank placeholder frame
            return {
                "frame_b64": "",
                "timestamp": timestamp,
                "width": width,
                "height": height,
                "valid": False,
                "error": str(e),
            }

    def cancel(self) -> None:
        """Cancel any in-progress frame grab."""
        if self._frame_grabber is not None:
            self._frame_grabber.cancel()


# Global instance for reuse
_preview_service: PreviewService | None = None


def get_preview_service() -> PreviewService:
    """Get or create the global preview service instance."""
    global _preview_service
    if _preview_service is None:
        _preview_service = PreviewService()
    return _preview_service
