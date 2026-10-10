"""Serial bridge for Arduino-class physical I/O devices.

The host is only a serial transport. Coreless decides what to do with events;
the Arduino exposes physical pins and reports sensor/input events.

Wire format: one UTF-8 JSON object per newline, protocol version 1. This module
uses a duck-typed serial object (write/readline), so pyserial is optional.
"""
from __future__ import annotations

import json
import math
import time
from typing import Any, Protocol

from host_io import InputTransport, encode_input_event
from input import CoordinateFrame, InputEvent, InputEventType

PROTOCOL_VERSION = 1
MAX_FRAME_BYTES = 4096


def discover_serial_devices(
    port_provider=None,
    *,
    vendor_ids: set[int] | frozenset[int] | None = None,
    product_ids: set[int] | frozenset[int] | None = None,
    serial_number: str | None = None,
) -> tuple[dict[str, object], ...]:
    """Enumerate serial ports without opening them or requiring pyserial.

    A caller may inject a provider (typically serial.tools.list_ports.comports)
    for deterministic testing. If no provider is supplied, pyserial's optional
    list_ports module is loaded lazily. VID/PID and serial-number filters are
    exact matches; omitted filters leave the corresponding attribute unfiltered.
    Returned records contain only stable, useful discovery metadata.
    """
    if port_provider is None:
        try:
            from serial.tools.list_ports import comports
        except ImportError as exc:
            raise RuntimeError(
                "serial discovery requires pyserial or an explicit port_provider"
            ) from exc
        port_provider = comports
    if not callable(port_provider):
        raise TypeError("port_provider must be callable")
    if serial_number is not None and (
        not isinstance(serial_number, str) or not serial_number.strip()
    ):
        raise ValueError("serial_number must be a non-empty string or null")

    found: list[dict[str, object]] = []
    for port in port_provider():
        device = getattr(port, "device", None)
        if not isinstance(device, str) or not device:
            continue
        vid = getattr(port, "vid", None)
        pid = getattr(port, "pid", None)
        serial = getattr(port, "serial_number", None)
        if vendor_ids is not None and vid not in vendor_ids:
            continue
        if product_ids is not None and pid not in product_ids:
            continue
        if serial_number is not None and serial != serial_number:
            continue
        found.append({
            "device": device,
            "description": str(getattr(port, "description", "") or ""),
            "hwid": str(getattr(port, "hwid", "") or ""),
            "vid": vid,
            "pid": pid,
            "serial_number": serial,
        })
    found.sort(key=lambda item: str(item["device"]).casefold())
    return tuple(found)
_COMMANDS = frozenset({"digital_write", "analog_write", "pin_mode", "digital_read", "analog_read"})
_PIN_MODES = frozenset({"input", "input_pullup", "output"})


class SerialPort(Protocol):
    def write(self, data: bytes) -> Any: ...
    def readline(self) -> bytes: ...


def _strict_int(value: object, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} is out of range")
    return value


def encode_message(kind: str, device_id: str, sequence: int, payload: dict) -> bytes:
    """Encode one bounded Arduino bridge message."""
    if kind not in {"command", "event", "ack", "error"}:
        raise ValueError("unsupported Arduino message kind")
    if not isinstance(device_id, str) or not device_id.strip():
        raise ValueError("device_id must not be empty")
    _strict_int(sequence, "sequence", 0, 0x7FFFFFFF)
    if not isinstance(payload, dict):
        raise TypeError("payload must be a JSON object")
    message = {
        "protocol": PROTOCOL_VERSION,
        "kind": kind,
        "device_id": device_id,
        "sequence": sequence,
        "payload": payload,
    }
    encoded = json.dumps(message, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n"
    if len(encoded) > MAX_FRAME_BYTES:
        raise ValueError("Arduino message exceeds maximum frame size")
    return encoded


def decode_message(frame: bytes, *, expected_device_id: str | None = None) -> dict:
    """Decode and strictly validate one newline-delimited serial message."""
    if not isinstance(frame, (bytes, bytearray, memoryview)):
        raise TypeError("Arduino frame must be bytes-like")
    raw = bytes(frame)
    if not raw.endswith(b"\n"):
        raise ValueError("Arduino frame is not newline terminated")
    if len(raw) > MAX_FRAME_BYTES:
        raise ValueError("Arduino frame exceeds maximum frame size")
    try:
        message = json.loads(raw[:-1].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid Arduino JSON frame") from exc
    if not isinstance(message, dict):
        raise ValueError("Arduino frame must contain a JSON object")
    if message.get("protocol") != PROTOCOL_VERSION or isinstance(message.get("protocol"), bool):
        raise ValueError("unsupported Arduino protocol version")
    kind = message.get("kind")
    if kind not in {"command", "event", "ack", "error"}:
        raise ValueError("unsupported Arduino message kind")
    device_id = message.get("device_id")
    if not isinstance(device_id, str) or not device_id.strip():
        raise ValueError("device_id must not be empty")
    if expected_device_id is not None and device_id != expected_device_id:
        raise ValueError("Arduino device identity mismatch")
    _strict_int(message.get("sequence"), "sequence", 0, 0x7FFFFFFF)
    if not isinstance(message.get("payload"), dict):
        raise ValueError("payload must be a JSON object")
    return message


class ArduinoSerialIO:
    """Validated Coreless-to-Arduino command/event bridge over a serial port.

    Instantiate with a serial object such as serial.Serial(...). Opening and
    closing the physical port is deliberately owned by the caller.
    """

    def __init__(self, serial_port: SerialPort, device_id: str) -> None:
        if not callable(getattr(serial_port, "write", None)) or not callable(
            getattr(serial_port, "readline", None)
        ):
            raise TypeError("serial_port must provide write() and readline()")
        if not isinstance(device_id, str) or not device_id.strip():
            raise ValueError("device_id must not be empty")
        self._serial = serial_port
        self.device_id = device_id
        self._next_sequence = 0
        self._last_received_sequence = -1

    def send_command(self, operation: str, *, pin: int, value: int | str | None = None) -> int:
        """Send one allowlisted pin command and return its sequence number."""
        if operation not in _COMMANDS:
            raise ValueError("unsupported Arduino operation")
        pin = _strict_int(pin, "pin", 0, 255)
        payload: dict[str, Any] = {"op": operation, "pin": pin}
        if operation == "pin_mode":
            if value not in _PIN_MODES:
                raise ValueError("pin_mode value is unsupported")
            payload["value"] = value
        elif operation in {"digital_write", "analog_write"}:
            maximum = 1 if operation == "digital_write" else 255
            payload["value"] = _strict_int(value, "value", 0, maximum)
        elif value is not None:
            raise ValueError("read operations do not accept a value")
        sequence = self._next_sequence
        frame = encode_message("command", self.device_id, sequence, payload)
        written = self._serial.write(frame)
        if written is not None and written != len(frame):
            raise IOError("short write to Arduino serial transport")
        self._next_sequence += 1
        return sequence

    def receive_message(self) -> dict:
        """Read one event/ack/error message, rejecting stale or misrouted frames."""
        frame = self._serial.readline()
        message = decode_message(frame, expected_device_id=self.device_id)
        if message["kind"] == "command":
            raise ValueError("Arduino sent a host-only command message")
        sequence = message["sequence"]
        if sequence <= self._last_received_sequence:
            raise ValueError("Arduino message sequence is not increasing")
        self._last_received_sequence = sequence
        if message["kind"] == "error":
            detail = message["payload"].get("message", "unspecified Arduino error")
            if not isinstance(detail, str):
                raise ValueError("Arduino error message must be a string")
            raise RuntimeError(f"Arduino reported error: {detail}")
        return message

    def receive_event(self) -> dict:
        """Read the next sensor/input event; acknowledgements are not events."""
        message = self.receive_message()
        if message["kind"] != "event":
            raise ValueError("next Arduino message is not an event")
        return message



class ArduinoInputAdapter:
    """Translate Arduino events into the existing Coreless input-event stream.

    Sensor readings and GPIO state changes become DEVICE_STATE events by
    default. Firmware may opt into a typed input event by including a valid
    event_type plus supported fields in the event payload.
    """

    def __init__(self, bridge: ArduinoSerialIO, input_transport: InputTransport) -> None:
        if not isinstance(bridge, ArduinoSerialIO):
            raise TypeError("bridge must be an ArduinoSerialIO")
        if not callable(getattr(input_transport, "send_event", None)):
            raise TypeError("input_transport must implement send_event(bytes)")
        self.bridge = bridge
        self.input_transport = input_transport
        self.events_forwarded = 0
        self.acknowledgements_seen = 0

    def _to_coreless_event(self, message: dict) -> InputEvent:
        payload = message["payload"]
        raw_type = payload.get("event_type", InputEventType.DEVICE_STATE.value)
        try:
            event_type = InputEventType(raw_type)
        except (ValueError, TypeError) as exc:
            raise ValueError("Arduino event has unsupported event_type") from exc

        def optional_number(name: str) -> float | None:
            value = payload.get(name)
            if value is None:
                return None
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"Arduino event {name} must be numeric")
            if not math.isfinite(value):
                raise ValueError(f"Arduino event {name} must be finite")
            return float(value)

        contact_id = payload.get("contact_id")
        if contact_id is not None and (
            isinstance(contact_id, bool) or not isinstance(contact_id, int)
        ):
            raise ValueError("Arduino event contact_id must be an integer")
        button = payload.get("button")
        if button is not None and (
            isinstance(button, bool) or not isinstance(button, int)
        ):
            raise ValueError("Arduino event button must be an integer")

        x = optional_number("x")
        y = optional_number("y")
        if (x is None) != (y is None):
            raise ValueError("Arduino event coordinates must include both x and y")

        metadata = {
            "source": "arduino",
            "arduino_sequence": message["sequence"],
            "payload": payload,
        }
        return InputEvent(
            abi_version=InputEvent.ABI_VERSION,
            event_type=event_type,
            device_id=self.bridge.device_id,
            timestamp_ns=time.monotonic_ns(),
            sequence=message["sequence"],
            coordinate_frame=CoordinateFrame.HOST,
            x=x,
            y=y,
            contact_id=contact_id,
            pressure=optional_number("pressure"),
            button=button,
            metadata=metadata,
        )

    def pump_once(self) -> bool:
        """Read one serial message; forward events, ignore acknowledgements.

        Returns True when a Coreless input event was forwarded, False for an
        acknowledgement. Device errors and malformed messages remain visible
        to the caller instead of being silently discarded.
        """
        message = self.bridge.receive_message()
        if message["kind"] == "ack":
            self.acknowledgements_seen += 1
            return False
        if message["kind"] != "event":
            raise ValueError("unexpected Arduino message kind")
        event = self._to_coreless_event(message)
        self.input_transport.send_event(encode_input_event(event))
        self.events_forwarded += 1
        return True
