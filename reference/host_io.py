"""Concrete deterministic host I/O channel adapters for Coreless.

These adapters terminate the existing transport-neutral host contract in
memory so display, input, and network paths can be tested end-to-end without
moving computation into the host or pretending physical buses are complete.
"""

from __future__ import annotations

import json
import math
from collections import deque
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from input import CoordinateFrame, InputEvent, InputEventType


class HostIOQueueEmpty(RuntimeError):
    """Raised only when a memory host transport has no queued item."""


@runtime_checkable
class DisplayTransport(Protocol):
    """Host-side display channel contract."""

    def send_frame(self, frame: bytes) -> None:
        ...

    def receive_frame(self) -> bytes:
        ...


@runtime_checkable
class InputTransport(Protocol):
    """Host-side input channel contract."""

    def send_event(self, event: bytes) -> None:
        ...

    def receive_event(self) -> bytes:
        ...


@runtime_checkable
class NetworkTransport(Protocol):
    """Host-side network channel contract."""

    def send_packet(self, packet: bytes) -> None:
        ...

    def receive_packet(self) -> bytes:
        ...


def encode_input_event(event: InputEvent) -> bytes:
    """Encode one Coreless input event for the host input transport."""
    def validate_metadata(item, path="metadata") -> None:
        if item is None or isinstance(item, (str, bool, int)):
            return
        if isinstance(item, float):
            if not math.isfinite(item):
                raise ValueError(f"{path} must contain only finite numbers")
            return
        if isinstance(item, dict):
            for key, nested in item.items():
                if not isinstance(key, str):
                    raise ValueError(f"{path} object keys must be strings")
                validate_metadata(nested, f"{path}.{key}")
            return
        if isinstance(item, list):
            for index, nested in enumerate(item):
                validate_metadata(nested, f"{path}[{index}]")
            return
        raise ValueError(f"{path} contains unsupported metadata type: {type(item).__name__}")

    validate_metadata(dict(event.metadata))
    payload = {
        "abi_version": event.abi_version,
        "event_type": event.event_type.value,
        "device_id": event.device_id,
        "timestamp_ns": event.timestamp_ns,
        "sequence": event.sequence,
        "coordinate_frame": event.coordinate_frame.value,
        "x": event.x,
        "y": event.y,
        "contact_id": event.contact_id,
        "pressure": event.pressure,
        "button": event.button,
        "metadata": dict(event.metadata),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def decode_input_event(payload: bytes) -> InputEvent:
    """Decode and validate one host input frame without coercing field types."""
    if not isinstance(payload, (bytes, bytearray, memoryview)):
        raise TypeError("input event payload must be bytes-like")
    def reject_nonfinite_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON number is not allowed: {value}")

    try:
        value = json.loads(
            bytes(payload).decode("utf-8"),
            parse_constant=reject_nonfinite_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError("invalid input event frame") from exc
    if not isinstance(value, dict):
        raise ValueError("input event frame must contain a JSON object")

    required = (
        "abi_version", "event_type", "device_id", "timestamp_ns",
        "sequence", "coordinate_frame",
    )
    missing = [name for name in required if name not in value]
    if missing:
        raise ValueError(f"input event frame missing required fields: {', '.join(missing)}")

    for name in ("abi_version", "timestamp_ns", "sequence"):
        if type(value[name]) is not int:
            raise ValueError(f"{name} must be an integer")
    for name in ("event_type", "device_id", "coordinate_frame"):
        if not isinstance(value[name], str):
            raise ValueError(f"{name} must be a string")

    metadata = value.get("metadata", {})
    if not isinstance(metadata, dict):
        raise ValueError("metadata must be a JSON object")

    def validate_finite_metadata(item, path="metadata"):
        if isinstance(item, float) and not math.isfinite(item):
            raise ValueError(f"{path} must contain only finite numbers")
        if isinstance(item, dict):
            for key, nested in item.items():
                validate_finite_metadata(nested, f"{path}.{key}")
        elif isinstance(item, list):
            for index, nested in enumerate(item):
                validate_finite_metadata(nested, f"{path}[{index}]")

    validate_finite_metadata(metadata)

    for name in ("contact_id", "button"):
        item = value.get(name)
        if item is not None and type(item) is not int:
            raise ValueError(f"{name} must be an integer or null")
    for name in ("x", "y", "pressure"):
        item = value.get(name)
        if item is not None and (isinstance(item, bool) or not isinstance(item, (int, float))):
            raise ValueError(f"{name} must be a number or null")
        if item is not None and not math.isfinite(item):
            raise ValueError(f"{name} must be finite or null")

    return InputEvent(
        abi_version=value["abi_version"],
        event_type=InputEventType(value["event_type"]),
        device_id=value["device_id"],
        timestamp_ns=value["timestamp_ns"],
        sequence=value["sequence"],
        coordinate_frame=CoordinateFrame(value["coordinate_frame"]),
        x=value.get("x"),
        y=value.get("y"),
        contact_id=value.get("contact_id"),
        pressure=value.get("pressure"),
        button=value.get("button"),
        metadata=metadata,
    )


@dataclass
class MemoryDisplayTransport:
    """Frame-oriented display sink/source used by the reference host boundary."""

    frames: deque[bytes] = field(default_factory=deque)

    def send_frame(self, frame: bytes) -> None:
        if not isinstance(frame, (bytes, bytearray, memoryview)):
            raise TypeError("display frame must be bytes-like")
        self.frames.append(bytes(frame))

    def receive_frame(self) -> bytes:
        if not self.frames:
            raise HostIOQueueEmpty("display transport has no queued frame")
        return self.frames.popleft()


@dataclass
class MemoryInputTransport:
    """Ordered input-event transport preserving the raw event payload."""

    events: deque[bytes] = field(default_factory=deque)

    def send_event(self, event: bytes) -> None:
        if not isinstance(event, (bytes, bytearray, memoryview)):
            raise TypeError("input event must be bytes-like")
        self.events.append(bytes(event))

    def receive_event(self) -> bytes:
        if not self.events:
            raise HostIOQueueEmpty("input transport has no queued event")
        return self.events.popleft()


@dataclass
class MemoryNetworkTransport:
    """Packet transport for deterministic host-network boundary tests."""

    packets: deque[bytes] = field(default_factory=deque)

    def send_packet(self, packet: bytes) -> None:
        if not isinstance(packet, (bytes, bytearray, memoryview)):
            raise TypeError("network packet must be bytes-like")
        self.packets.append(bytes(packet))

    def receive_packet(self) -> bytes:
        if not self.packets:
            raise HostIOQueueEmpty("network transport has no queued packet")
        return self.packets.popleft()


@runtime_checkable
class HostIO(Protocol):
    """Bundle contract for the three negotiated external I/O channels."""

    display: DisplayTransport
    input: InputTransport
    network: NetworkTransport


@dataclass
class MemoryHostIO:
    """Convenience bundle for the three primary external I/O transports."""

    display: MemoryDisplayTransport = field(default_factory=MemoryDisplayTransport)
    input: MemoryInputTransport = field(default_factory=MemoryInputTransport)
    network: MemoryNetworkTransport = field(default_factory=MemoryNetworkTransport)
