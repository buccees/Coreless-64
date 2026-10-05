"""Coreless pointer/touch input boundary and optional VIGIL adapter.

The host provides physical input transport. Coreless owns device assignment and
raw-event routing. VIGIL may consume raw events and return derived events.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Protocol


class InputEventType(str, Enum):
    POINTER_MOVE = "pointer_move"
    POINTER_BUTTON = "pointer_button"
    TOUCH_BEGIN = "touch_begin"
    TOUCH_UPDATE = "touch_update"
    TOUCH_END = "touch_end"
    STYLUS = "stylus"
    DEVICE_STATE = "device_state"


class CoordinateFrame(str, Enum):
    HOST = "host"
    CORELESS = "coreless"
    DISPLAY = "display"
    VIGIL = "vigil"


@dataclass(frozen=True)
class InputCapabilities:
    pointer: bool = False
    absolute: bool = False
    relative: bool = False
    touch: bool = False
    multitouch: bool = False
    stylus: bool = False
    pressure: bool = False
    buttons: int = 0

    def supports(self, event_type: InputEventType) -> bool:
        return {
            InputEventType.POINTER_MOVE: self.pointer,
            InputEventType.POINTER_BUTTON: self.pointer and self.buttons > 0,
            InputEventType.TOUCH_BEGIN: self.touch,
            InputEventType.TOUCH_UPDATE: self.touch,
            InputEventType.TOUCH_END: self.touch,
            InputEventType.STYLUS: self.stylus,
            InputEventType.DEVICE_STATE: True,
        }[event_type]


@dataclass(frozen=True)
class PointingDevice:
    device_id: str
    name: str
    capabilities: InputCapabilities
    host_identity: str | None = None

    def __post_init__(self) -> None:
        if not self.device_id:
            raise ValueError("device_id must not be empty")
        if not self.name:
            raise ValueError("name must not be empty")


@dataclass(frozen=True)
class InputEvent:
    abi_version: int
    event_type: InputEventType
    device_id: str
    timestamp_ns: int
    sequence: int
    coordinate_frame: CoordinateFrame
    x: float | None = None
    y: float | None = None
    contact_id: int | None = None
    pressure: float | None = None
    button: int | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    ABI_VERSION = 1

    def __post_init__(self) -> None:
        if self.abi_version != self.ABI_VERSION:
            raise ValueError("unsupported input ABI version")
        if not self.device_id:
            raise ValueError("device_id must not be empty")
        if self.timestamp_ns < 0:
            raise ValueError("timestamp_ns must be non-negative")
        if self.sequence < 0:
            raise ValueError("sequence must be non-negative")
        if self.x is not None and self.y is None:
            raise ValueError("x and y must be supplied together")
        if self.y is not None and self.x is None:
            raise ValueError("x and y must be supplied together")


@dataclass(frozen=True)
class InterpretedInputEvent:
    interpretation_id: str
    kind: str
    device_id: str
    timestamp_ns: int
    source_sequence: tuple[int, ...]
    metadata: Mapping[str, object] = field(default_factory=dict)
    confidence: float | None = None

    def __post_init__(self) -> None:
        if not self.interpretation_id:
            raise ValueError("interpretation_id must not be empty")
        if not self.kind:
            raise ValueError("kind must not be empty")
        if not self.source_sequence:
            raise ValueError("source_sequence must not be empty")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


class VigilInputInterpreter(Protocol):
    """Minimal VIGIL-side contract consumed by Coreless."""

    def available(self) -> bool:
        ...

    def interpret(
        self,
        event: InputEvent,
        device: PointingDevice,
    ) -> tuple[InterpretedInputEvent, ...]:
        ...


class PointingDeviceManager:
    """Owns discovery, logical designation, binding, and failover."""

    def __init__(self) -> None:
        self._devices: dict[str, PointingDevice] = {}
        self._designated_device_id: str | None = None
        self._bound_device_id: str | None = None

    @property
    def designated_device_id(self) -> str | None:
        return self._designated_device_id

    @property
    def bound_device_id(self) -> str | None:
        return self._bound_device_id

    def discover(self, devices: list[PointingDevice] | tuple[PointingDevice, ...]) -> None:
        self._devices = {device.device_id: device for device in devices}
        if self._designated_device_id in self._devices:
            self._bound_device_id = self._designated_device_id
        else:
            self._bound_device_id = None

    def designate(self, device_id: str) -> None:
        if device_id not in self._devices:
            raise KeyError(f"unknown pointing device: {device_id}")
        self._designated_device_id = device_id
        self._bound_device_id = device_id

    def clear_designation(self) -> None:
        self._designated_device_id = None
        self._bound_device_id = None

    def reassign(self, device_id: str) -> None:
        self.designate(device_id)

    def failover(self, device_id: str | None = None) -> str | None:
        if device_id is not None:
            self.designate(device_id)
            return self._bound_device_id
        for candidate in self._devices.values():
            if candidate.device_id != self._designated_device_id:
                self._bound_device_id = candidate.device_id
                return self._bound_device_id
        self._bound_device_id = None
        return None

    def bound_device(self) -> PointingDevice | None:
        if self._bound_device_id is None:
            return None
        return self._devices.get(self._bound_device_id)

    def persistent_state(self) -> dict[str, object]:
        return {"designated_device_id": self._designated_device_id}

    def restore_state(self, state: Mapping[str, object]) -> None:
        value = state.get("designated_device_id")
        if value is not None and not isinstance(value, str):
            raise ValueError("designated_device_id must be a string or null")
        self._designated_device_id = value
        self._bound_device_id = value if value in self._devices else None


class CorelessInputRouter:
    """Routes raw Coreless input and optionally sends it to VIGIL."""

    VERSION = 1

    def __init__(
        self,
        devices: PointingDeviceManager | None = None,
        vigil: VigilInputInterpreter | None = None,
    ) -> None:
        self.devices = devices or PointingDeviceManager()
        self.vigil = vigil
        self.vigil_enabled = vigil is not None
        self._raw_events: list[InputEvent] = []
        self._interpreted_events: list[InterpretedInputEvent] = []

    @property
    def raw_events(self) -> tuple[InputEvent, ...]:
        return tuple(self._raw_events)

    @property
    def interpreted_events(self) -> tuple[InterpretedInputEvent, ...]:
        return tuple(self._interpreted_events)

    def enable_vigil(self, enabled: bool = True) -> None:
        self.vigil_enabled = enabled

    def submit(self, event: InputEvent) -> tuple[InterpretedInputEvent, ...]:
        device = self.devices.bound_device()
        if device is None:
            raise RuntimeError("no pointing device is bound")
        if event.device_id != device.device_id:
            raise PermissionError("event device is not the bound pointing device")
        if not device.capabilities.supports(event.event_type):
            raise ValueError("event type is not supported by the device")
        if self._raw_events and event.sequence <= self._raw_events[-1].sequence:
            raise ValueError("input event sequence must increase monotonically")
        self._raw_events.append(event)

        if not self.vigil_enabled or self.vigil is None or not self.vigil.available():
            return ()

        derived = self.vigil.interpret(event, device)
        self._interpreted_events.extend(derived)
        return derived

    def persistent_state(self) -> dict[str, object]:
        return {
            "version": self.VERSION,
            "vigil_enabled": self.vigil_enabled,
            "device": self.devices.persistent_state(),
        }

    def restore_state(self, state: Mapping[str, object]) -> None:
        if int(state.get("version", self.VERSION)) != self.VERSION:
            raise ValueError("unsupported input state version")
        self.vigil_enabled = bool(state.get("vigil_enabled", self.vigil_enabled))
        device_state = state.get("device", {})
        if not isinstance(device_state, Mapping):
            raise ValueError("device state must be a mapping")
        self.devices.restore_state(device_state)
