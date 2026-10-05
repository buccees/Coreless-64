"""Low-latency camera fast path for VIGIL visual touch input."""
from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from .coordinate import CameraDisplayMapper
from .model import Detection
from .spatial import CameraFrame
from .visual_pointer import VisualPointer, VisualTouchIntent


class FastTouchDetector(Protocol):
    """Minimal detector contract for camera-to-touch fast-path implementations."""

    def detect(self, frame: CameraFrame) -> Detection | None:
        ...


class FastCameraTouchPath:
    """Process shared or direct camera frames into visual touch intents."""

    def __init__(
        self,
        camera: object,
        detector: FastTouchDetector,
        *,
        pointer: VisualPointer | None = None,
        display_width: int | None = None,
        display_height: int | None = None,
    ) -> None:
        if not hasattr(camera, "available") or not (
            hasattr(camera, "read") or hasattr(camera, "latest")
        ):
            raise TypeError("camera must provide available() and read()/latest()")
        if (display_width is None) != (display_height is None):
            raise ValueError("display_width and display_height must be supplied together")
        self.camera = camera
        self.detector = detector
        self.pointer = pointer or VisualPointer()
        self.display_width = display_width
        self.display_height = display_height
        self.frames_processed = 0
        self.last_frame_sequence: int | None = None
        self.last_detection: Detection | None = None

    def poll(self) -> VisualTouchIntent | None:
        """Process the newest shared frame without reading the physical camera."""
        if not self.camera.available():
            return None
        frame = self.camera.latest() if hasattr(self.camera, "latest") else self.camera.read()
        if frame is None:
            return None
        if self.last_frame_sequence is not None and frame.sequence <= self.last_frame_sequence:
            return None
        return self.process_frame(frame)

    def process_frame(self, frame: CameraFrame) -> VisualTouchIntent | None:
        self.frames_processed += 1
        self.last_frame_sequence = frame.sequence
        detection = self.detector.detect(frame)
        if detection is None:
            if self.pointer.active and self.last_detection is not None:
                intent = self.pointer.release(self.last_detection)
                return self._map_intent(intent, frame)
            return None
        self.last_detection = detection
        return self._map_intent(self.pointer.update(detection), frame)

    def _map_intent(
        self,
        intent: VisualTouchIntent | None,
        frame: CameraFrame,
    ) -> VisualTouchIntent | None:
        if intent is None or self.display_width is None or self.display_height is None:
            return intent
        mapper = CameraDisplayMapper(
            frame.width,
            frame.height,
            self.display_width,
            self.display_height,
        )
        x, y = mapper.map(intent.x, intent.y)
        return replace(intent, x=x, y=y)
