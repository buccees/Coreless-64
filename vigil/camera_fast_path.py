"""Direct low-latency camera path for VIGIL touch cues."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .spatial import CameraFrame
from .visual_pointer import VisualPointer, VisualTouchIntent


class FastCameraSource(Protocol):
    def read(self) -> CameraFrame | None:
        ...


class TouchCueDetector(Protocol):
    def detect_touch_cue(self, frame: CameraFrame) -> object | None:
        ...


@dataclass
class CameraTouchFastPath:
    """Camera -> touch cue -> intent, without general perception stages."""

    camera: FastCameraSource
    detector: TouchCueDetector
    pointer: VisualPointer

    def poll(self) -> VisualTouchIntent | None:
        frame = self.camera.read()
        if frame is None:
            return None
        detection = self.detector.detect_touch_cue(frame)
        if detection is None:
            return None
        return self.pointer.update(detection)  # type: ignore[arg-type]

    def release(self, detection: object) -> VisualTouchIntent | None:
        return self.pointer.release(detection)  # type: ignore[arg-type]
