"""Serial bridge for Arduino-class physical I/O devices.

The host is only a serial transport. Coreless decides what to do with events;
the Arduino exposes physical pins and reports sensor/input events.

Wire format: one UTF-8 JSON object per newline, protocol version 1. This module
uses a duck-typed serial object (write/readline), so pyserial is optional.
"""
from __future__ import annotations

import json
from typing import Any, Protocol

PROTOCOL_VERSION = 1
MAX_FRAME_BYTES = 4096
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
