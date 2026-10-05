"""Optional VIGIL input intelligence for Coreless-64.

VIGIL consumes Coreless raw input and optional camera frames. Coreless remains
the authority for device assignment and raw event routing; this layer only
produces interpreted information.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Protocol

from reference.input import (
    InputEvent,
    InterpretedInputEvent,
    PointingDevice,
)

from .gesture import GestureInterpreter
from .spatial import CameraFrame


class CameraSource(Protocol):
    """Optional camera source. No camera is required for normal Coreless input."""

    def available(self) -> bool:
        ...

    def read(self) -> CameraFrame | None:
        ...


class VigilInputInterpreter(Protocol):
    def available(self) -> bool:
        ...

    def interpret(
        self,
        event: InputEvent,
        device: PointingDevice,
    ) -> tuple[InterpretedInputEvent, ...]:
        ...


@dataclass
class VigilInputLayer:
    """Small deterministic VIGIL layer that can be attached to CorelessInputRouter.

    The initial implementation deliberately does not depend on OpenCV, a camera
    driver, or an ML model. It establishes the stable boundary first so those
    optional capabilities can be added behind it later.
    """

    enabled: bool = False
    camera: CameraSource | None = None
    _camera_sequence: int = 0
    _last_event_sequence: int | None = None
    _camera_frames: list[CameraFrame] = field(default_factory=list)
    _gesture: GestureInterpreter = field(default_factory=GestureInterpreter)

    def available(self) -> bool:
        return self.enabled

    def enable(self, enabled: bool = True) -> None:
        self.enabled = enabled

    def interpret(
        self,
        event: InputEvent,
        device: PointingDevice,
    ) -> tuple[InterpretedInputEvent, ...]:
        if not self.enabled:
            return ()
        if self._last_event_sequence is not None and event.sequence <= self._last_event_sequence:
            raise ValueError("VIGIL input sequence must increase monotonically")
        self._last_event_sequence = event.sequence

        results = self._gesture.process(event)
        events = [
            InterpretedInputEvent(
                interpretation_id=f"vigil-input-{event.sequence}",
                kind=f"input.{event.event_type.value}",
                device_id=device.device_id,
                timestamp_ns=event.timestamp_ns,
                source_sequence=(event.sequence,),
                metadata={
                    "coordinate_frame": event.coordinate_frame.value,
                    "source": "coreless-input",
                },
                confidence=1.0,
            )
        ]
        for index, result in enumerate(results):
            events.append(
                InterpretedInputEvent(
                    interpretation_id=f"vigil-gesture-{event.sequence}-{index}",
                    kind=f"gesture.{result.gesture}",
                    device_id=device.device_id,
                    timestamp_ns=event.timestamp_ns,
                    source_sequence=result.source_sequence,
                    metadata={
                        "coordinate_frame": event.coordinate_frame.value,
                        "contacts": result.contacts,
                        **dict(result.metadata or {}),
                        "source": "vigil-gesture",
                    },
                    confidence=result.confidence,
                )
            )
        return tuple(events)

    def ingest_camera_frame(self, frame: CameraFrame) -> None:
        if not self.enabled:
            raise RuntimeError("VIGIL is disabled")
        if self._camera_frames and frame.sequence <= self._camera_frames[-1].sequence:
            raise ValueError("camera frame sequence must increase monotonically")
        self._camera_frames.append(frame)
        self._camera_sequence = frame.sequence

    def poll_camera(self) -> CameraFrame | None:
        if not self.enabled or self.camera is None or not self.camera.available():
            return None
        frame = self.camera.read()
        if frame is not None:
            self.ingest_camera_frame(frame)
        return frame

    @property
    def camera_frames(self) -> tuple[CameraFrame, ...]:
        return tuple(self._camera_frames)

    def persistent_state(self) -> dict[str, object]:
        return {
            "version": 1,
            "enabled": self.enabled,
            "camera_enabled": self.camera is not None,
        }

    def restore_state(self, state: Mapping[str, object]) -> None:
        if int(state.get("version", 1)) != 1:
            raise ValueError("unsupported VIGIL state version")
        self.enabled = bool(state.get("enabled", False))
