"""Coreless pointer/touch input boundary and optional VIGIL adapter.

The host provides physical input transport. Coreless owns device assignment and
raw-event routing. VIGIL may consume raw events and return derived events.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from types import MappingProxyType
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
        if isinstance(self.abi_version, bool) or not isinstance(self.abi_version, int):
            raise ValueError("input ABI version must be an integer")
        if self.abi_version != self.ABI_VERSION:
            raise ValueError("unsupported input ABI version")
        if not isinstance(self.event_type, InputEventType):
            raise ValueError("event_type must be a supported InputEventType")
        if not isinstance(self.coordinate_frame, CoordinateFrame):
            raise ValueError("coordinate_frame must be a supported CoordinateFrame")
        if not isinstance(self.device_id, str) or not self.device_id.strip():
            raise ValueError("device_id must not be empty")
        if isinstance(self.timestamp_ns, bool) or not isinstance(self.timestamp_ns, int):
            raise ValueError("timestamp_ns must be an integer")
        if self.timestamp_ns < 0:
            raise ValueError("timestamp_ns must be non-negative")
        if isinstance(self.sequence, bool) or not isinstance(self.sequence, int):
            raise ValueError("sequence must be an integer")
        if self.sequence < 0:
            raise ValueError("sequence must be non-negative")
        if (self.x is None) != (self.y is None):
            raise ValueError("x and y must be supplied together")
        if self.x is not None:
            for coordinate in (self.x, self.y):
                if (
                    isinstance(coordinate, bool)
                    or not isinstance(coordinate, (int, float))
                    or not math.isfinite(coordinate)
                ):
                    raise ValueError("coordinates must be finite numbers")
        if self.pressure is not None and (
            isinstance(self.pressure, bool)
            or not isinstance(self.pressure, (int, float))
            or not math.isfinite(self.pressure)
        ):
            raise ValueError("pressure must be a finite number")
        if self.contact_id is not None and (
            isinstance(self.contact_id, bool) or not isinstance(self.contact_id, int)
        ):
            raise ValueError("contact_id must be an integer or null")
        if self.button is not None and (
            isinstance(self.button, bool) or not isinstance(self.button, int)
        ):
            raise ValueError("button must be an integer or null")
        if not isinstance(self.metadata, Mapping):
            raise ValueError("metadata must be a mapping")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


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
        if not isinstance(self.interpretation_id, str) or not self.interpretation_id.strip():
            raise ValueError("interpretation_id must not be empty")
        if not isinstance(self.kind, str) or not self.kind.strip():
            raise ValueError("kind must not be empty")
        if not isinstance(self.device_id, str) or not self.device_id.strip():
            raise ValueError("device_id must not be empty")
        if isinstance(self.timestamp_ns, bool) or not isinstance(self.timestamp_ns, int):
            raise ValueError("timestamp_ns must be an integer")
        if self.timestamp_ns < 0:
            raise ValueError("timestamp_ns must be non-negative")
        if not isinstance(self.source_sequence, tuple) or not self.source_sequence:
            raise ValueError("source_sequence must be a non-empty tuple")
        previous = -1
        for sequence in self.source_sequence:
            if (
                isinstance(sequence, bool)
                or not isinstance(sequence, int)
                or sequence < 0
                or sequence <= previous
            ):
                raise ValueError("source_sequence values must increase monotonically")
            previous = sequence
        if not isinstance(self.metadata, Mapping):
            raise ValueError("metadata must be a mapping")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))
        if self.confidence is not None and (
            isinstance(self.confidence, bool)
            or not isinstance(self.confidence, (int, float))
            or not math.isfinite(self.confidence)
            or not 0.0 <= self.confidence <= 1.0
        ):
            raise ValueError("confidence must be a finite number between 0 and 1")


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
    def devices(self) -> tuple[PointingDevice, ...]:
        return tuple(self._devices.values())

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
        self._last_sequence_by_device: dict[str, int] = {}
        self._last_timestamp_by_device: dict[str, int] = {}

    @property
    def raw_events(self) -> tuple[InputEvent, ...]:
        return tuple(self._raw_events)

    @property
    def interpreted_events(self) -> tuple[InterpretedInputEvent, ...]:
        return tuple(self._interpreted_events)

    def enable_vigil(self, enabled: bool = True) -> None:
        self.vigil_enabled = enabled

    def submit(self, event: InputEvent) -> tuple[InterpretedInputEvent, ...]:
        # Device-state telemetry can originate from any discovered device;
        # interactive pointer/touch events remain restricted to the designated
        # input device so a sensor board cannot steal keyboard/mouse focus.
        if event.event_type is InputEventType.DEVICE_STATE:
            device = next(
                (candidate for candidate in self.devices.devices
                 if candidate.device_id == event.device_id),
                None,
            )
            if device is None:
                raise PermissionError("event device is not a discovered Coreless input device")
        else:
            device = self.devices.bound_device()
            if device is None:
                raise RuntimeError("no pointing device is bound")
            if event.device_id != device.device_id:
                raise PermissionError("event device is not the bound pointing device")

        if not device.capabilities.supports(event.event_type):
            raise ValueError("event type is not supported by the device")
        previous_sequence = self._last_sequence_by_device.get(event.device_id, -1)
        if event.sequence <= previous_sequence:
            raise ValueError("input event sequence must increase monotonically")
        previous_timestamp = self._last_timestamp_by_device.get(event.device_id)
        if previous_timestamp is not None and event.timestamp_ns < previous_timestamp:
            raise ValueError("input event timestamp must not move backwards")
        self._last_sequence_by_device[event.device_id] = event.sequence
        self._last_timestamp_by_device[event.device_id] = event.timestamp_ns
        self._raw_events.append(event)

        # Device-state telemetry is retained as raw state and is not interpreted
        # as a pointer/touch gesture by VIGIL.
        if event.event_type is InputEventType.DEVICE_STATE:
            return ()
        if not self.vigil_enabled or self.vigil is None:
            return ()

        # VIGIL is optional: an adapter failure must never interrupt the raw
        # Coreless input path. Disable the failing interpreter for this router
        # instance and continue with ordinary pointer/touch handling.
        try:
            if not self.vigil.available():
                return ()
            derived = self.vigil.interpret(event, device)
            if not isinstance(derived, tuple):
                raise TypeError("VIGIL interpreter must return a tuple of derived events")
            for item in derived:
                if not isinstance(item, InterpretedInputEvent):
                    raise TypeError("VIGIL interpreter returned an invalid derived event")
                if item.device_id != event.device_id:
                    raise ValueError("VIGIL event device does not match raw input")
                if event.sequence not in item.source_sequence:
                    raise ValueError("VIGIL event provenance omits the triggering sequence")
                if max(item.source_sequence) > event.sequence:
                    raise ValueError("VIGIL event provenance references a future sequence")
        except Exception:
            self.vigil_enabled = False
            return ()

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
