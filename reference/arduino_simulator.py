"""Deterministic software model of the Coreless Arduino serial bridge.

This simulator exercises the firmware's newline-delimited JSON protocol without
claiming to model electrical behavior or real serial timing.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Mapping


PROTOCOL_VERSION = 1
MAX_LINE_BYTES = 255
MAX_SEQUENCE = 2**31 - 1


@dataclass
class VirtualArduino:
    """Protocol-level Arduino model for repeatable lifecycle tests.

    Disconnecting clears simulated output values. The accepted host sequence is
    retained across reconnects so an old command cannot become fresh merely
    because the transport was reopened.
    """

    device_id: str = "arduino-1"
    analog_inputs: Mapping[int, int] = field(default_factory=dict)
    digital_inputs: Mapping[int, int] = field(default_factory=dict)
    connected: bool = True
    pin_modes: dict[int, str] = field(default_factory=dict)
    digital_outputs: dict[int, int] = field(default_factory=dict)
    analog_outputs: dict[int, int] = field(default_factory=dict)
    last_host_sequence: int = -1
    device_sequence: int = 0

    def disconnect(self) -> None:
        """Close the virtual link and force all simulated outputs safe."""
        self.connected = False
        for pin in tuple(self.digital_outputs):
            self.digital_outputs[pin] = 0
        for pin in tuple(self.analog_outputs):
            self.analog_outputs[pin] = 0

    def reconnect(self) -> None:
        """Reopen the virtual link without restoring old output commands."""
        self.connected = True

    def sensor_event(self, pin: int = 0) -> bytes:
        """Return a deterministic analog sensor event as one JSON line."""
        if not self.connected:
            raise RuntimeError("virtual Arduino is disconnected")
        return self._encode(
            "event",
            {"sensor": "analog", "pin": f"A{pin}", "value": self._analog_read(pin)},
        )

    def process_line(self, line: str | bytes) -> bytes:
        """Process one host command and return one newline-terminated reply."""
        if not self.connected:
            raise RuntimeError("virtual Arduino is disconnected")
        if isinstance(line, bytes):
            try:
                text = line.decode("utf-8")
            except UnicodeDecodeError:
                return self._error("invalid UTF-8 command")
        elif isinstance(line, str):
            text = line
        else:
            raise TypeError("line must be str or bytes")

        text = text.rstrip("\r\n")
        if len(text.encode("utf-8")) > MAX_LINE_BYTES:
            return self._error("command line too long")
        try:
            message = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return self._error("invalid JSON command")
        if not isinstance(message, dict):
            return self._error("invalid JSON command")
        if type(message.get("protocol")) is not int or message["protocol"] != PROTOCOL_VERSION:
            return self._error("unsupported protocol version")
        if message.get("kind") != "command" or message.get("device_id") != self.device_id:
            return self._error("message kind or device identity mismatch")
        sequence = message.get("sequence")
        if type(sequence) is not int or not 0 <= sequence <= MAX_SEQUENCE:
            return self._error("invalid command sequence")
        if sequence <= self.last_host_sequence:
            return self._error("command sequence is not increasing")
        payload = message.get("payload")
        if not isinstance(payload, dict):
            return self._error("invalid payload")
        operation = payload.get("op", "")
        pin = self._integer(payload, "pin", 0, 255)
        if pin is None:
            return self._error("invalid pin")

        value: int | None = None
        if operation == "pin_mode":
            mode = payload.get("value", "")
            if mode not in ("input", "input_pullup", "output"):
                return self._error("invalid pin mode")
            self.pin_modes[pin] = mode
        elif operation == "digital_write":
            value = self._integer(payload, "value", 0, 1)
            if value is None:
                return self._error("invalid digital value")
            self.digital_outputs[pin] = value
        elif operation == "analog_write":
            value = self._integer(payload, "value", 0, 255)
            if value is None:
                return self._error("invalid analog value")
            self.analog_outputs[pin] = value
        elif operation == "digital_read":
            value = self.digital_inputs.get(pin, 0)
        elif operation == "analog_read":
            value = self._analog_read(pin)
        else:
            return self._error("unsupported operation")

        self.last_host_sequence = sequence
        ack_payload: dict[str, object] = {
            "request_sequence": sequence,
            "op": operation,
            "ok": True,
        }
        if value is not None:
            ack_payload["value"] = value
        return self._encode("ack", ack_payload)

    def _analog_read(self, pin: int) -> int:
        value = self.analog_inputs.get(pin, 0)
        if type(value) is not int or not 0 <= value <= 1023:
            raise ValueError("configured analog input must be an integer from 0 to 1023")
        return value

    @staticmethod
    def _integer(payload: dict, key: str, minimum: int, maximum: int) -> int | None:
        value = payload.get(key)
        if type(value) is not int or not minimum <= value <= maximum:
            return None
        return value

    def _error(self, message: str) -> bytes:
        return self._encode("error", {"message": message})

    def _encode(self, kind: str, payload: dict) -> bytes:
        message = {
            "protocol": PROTOCOL_VERSION,
            "kind": kind,
            "device_id": self.device_id,
            "sequence": self.device_sequence,
            "payload": payload,
        }
        self.device_sequence += 1
        return (json.dumps(message, separators=(",", ":"), sort_keys=True) + "\n").encode("utf-8")
