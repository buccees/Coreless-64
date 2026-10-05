"""Coreless adapter for VIGIL visual touch intents."""
from __future__ import annotations

from dataclasses import dataclass

from vigil.visual_pointer import VisualTouchIntent
from .input import (
    CoordinateFrame,
    CorelessInputRouter,
    InputCapabilities,
    InputEvent,
    InputEventType,
    PointingDevice,
)


@dataclass
class VisualPointingDeviceAdapter:
    """Materializes VIGIL visual touch intents as Coreless input events."""

    router: CorelessInputRouter
    device_id: str = "vigil.visual-pointer"
    name: str = "VIGIL Visual Pointer"
    contact_id: int = 0
    coordinate_frame: CoordinateFrame = CoordinateFrame.DISPLAY

    def register_and_designate(self) -> PointingDevice:
        device = PointingDevice(
            device_id=self.device_id,
            name=self.name,
            capabilities=InputCapabilities(
                pointer=True,
                absolute=True,
                touch=True,
                multitouch=True,
            ),
            host_identity=None,
        )
        devices = list(self.router.devices._devices.values())
        devices = [item for item in devices if item.device_id != self.device_id]
        devices.append(device)
        self.router.devices.discover(devices)
        self.router.devices.designate(self.device_id)
        return device

    def submit(self, intent: VisualTouchIntent) -> InputEvent:
        event_type = {
            "touch_begin": InputEventType.TOUCH_BEGIN,
            "move": InputEventType.TOUCH_UPDATE,
            "touch_end": InputEventType.TOUCH_END,
        }[intent.action]
        event = InputEvent(
            abi_version=InputEvent.ABI_VERSION,
            event_type=event_type,
            device_id=self.device_id,
            timestamp_ns=intent.timestamp_ns,
            sequence=self._next_sequence(),
            coordinate_frame=self.coordinate_frame,
            x=intent.x,
            y=intent.y,
            contact_id=self.contact_id,
            pressure=intent.confidence,
            metadata={
                "derived": True,
                "source": "vigil-visual-pointer",
                "detection_id": intent.detection_id,
                "camera_source_id": intent.source_id,
                "confidence": intent.confidence,
            },
        )
        self.router.submit(event)
        return event

    def _next_sequence(self) -> int:
        events = self.router.raw_events
        return events[-1].sequence + 1 if events else 0
