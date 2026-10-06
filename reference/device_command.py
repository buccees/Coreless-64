"""Transport-neutral Coreless-64 device command protocol.

This layer defines machine-to-machine commands above the physical transport.
A USB, PCIe, network, or other adapter carries these frames; it does not
change their meaning.
"""
from __future__ import annotations
from dataclasses import dataclass
import struct

MAGIC = b"CORECMD1"
PROTOCOL_VERSION = 1
OP_CAPABILITIES = 1
OP_READ = 2
OP_WRITE = 3
OP_EXECUTE = 4
OP_STATUS = 5
OP_SYNC = 6
FLAG_RESPONSE = 1
FLAG_ERROR = 2
_HEADER = struct.Struct("<8sHHIIQ")
HEADER_SIZE = _HEADER.size

@dataclass(frozen=True)
class DeviceCommand:
    opcode: int
    request_id: int
    payload: bytes = b""
    flags: int = 0
    protocol_version: int = PROTOCOL_VERSION

    def encode(self) -> bytes:
        if self.protocol_version != PROTOCOL_VERSION:
            raise ValueError("unsupported Coreless command protocol version")
        if not 0 <= self.opcode <= 0xFFFF:
            raise ValueError("opcode out of range")
        if not 0 <= self.request_id <= 0xFFFFFFFF:
            raise ValueError("request id out of range")
        if not 0 <= self.flags <= 0xFFFFFFFF:
            raise ValueError("flags out of range")
        if len(self.payload) > 0xFFFFFFFF:
            raise ValueError("command payload is too large")
        return _HEADER.pack(MAGIC, self.protocol_version, self.opcode,
                            self.request_id, len(self.payload), self.flags) + self.payload

    @classmethod
    def decode(cls, frame: bytes) -> "DeviceCommand":
        if len(frame) < HEADER_SIZE:
            raise ValueError("Coreless command frame is truncated")
        magic, version, opcode, request_id, length, flags = _HEADER.unpack(frame[:HEADER_SIZE])
        if magic != MAGIC:
            raise ValueError("invalid Coreless command magic")
        if version != PROTOCOL_VERSION:
            raise ValueError("unsupported Coreless command protocol version")
        payload = frame[HEADER_SIZE:]
        if len(payload) != length:
            raise ValueError("Coreless command payload length mismatch")
        return cls(opcode, request_id, payload, flags, version)

def response(request: DeviceCommand, payload: bytes = b"", *, error: bool = False) -> DeviceCommand:
    """Build a response retaining the request correlation identifier."""
    flags = FLAG_RESPONSE | (FLAG_ERROR if error else 0)
    return DeviceCommand(request.opcode, request.request_id, bytes(payload), flags)

def is_response(command: DeviceCommand) -> bool:
    return bool(command.flags & FLAG_RESPONSE)

def is_error(command: DeviceCommand) -> bool:
    return bool(command.flags & FLAG_ERROR)

def round_trip(command: DeviceCommand) -> DeviceCommand:
    """Encode and decode a command at the transport boundary."""
    return DeviceCommand.decode(command.encode())

def response_round_trip(request: DeviceCommand, payload: bytes = b"", *, error: bool = False) -> DeviceCommand:
    """Build and wire-round-trip a correlated device response."""
    return round_trip(response(request, payload, error=error))

def response_for(request: DeviceCommand, payload: bytes = b"", *, error: bool = False) -> DeviceCommand:
    """Build a correlated response and preserve the wire command version."""
    return response_round_trip(request, payload, error=error)

@dataclass(frozen=True)
class CommandPayload:
    """Deterministic structured payload for machine-to-machine commands."""
    operation: str
    data: bytes = b""

    def encode(self) -> bytes:
        name = self.operation.encode("utf-8")
        if not name or len(name) > 0xFFFF:
            raise ValueError("command operation name is invalid")
        return struct.pack("<H", len(name)) + name + self.data

    @classmethod
    def decode(cls, payload: bytes) -> "CommandPayload":
        if len(payload) < 2:
            raise ValueError("structured command payload is truncated")
        length = struct.unpack("<H", payload[:2])[0]
        if len(payload) < 2 + length:
            raise ValueError("structured command operation is truncated")
        try:
            operation = payload[2:2 + length].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("command operation is not valid UTF-8") from exc
        if not operation:
            raise ValueError("command operation must not be empty")
        return cls(operation, payload[2 + length:])
