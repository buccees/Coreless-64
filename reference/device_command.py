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
KNOWN_FLAGS = FLAG_RESPONSE | FLAG_ERROR
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
        if self.flags & ~KNOWN_FLAGS:
            raise ValueError("unsupported Coreless command flags")
        if self.flags & FLAG_ERROR and not self.flags & FLAG_RESPONSE:
            raise ValueError("Coreless error flag requires response flag")
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
        if flags & ~KNOWN_FLAGS:
            raise ValueError("unsupported Coreless command flags")
        if flags & FLAG_ERROR and not flags & FLAG_RESPONSE:
            raise ValueError("Coreless error flag requires response flag")
        payload = frame[HEADER_SIZE:]
        if len(payload) != length:
            raise ValueError("Coreless command payload length mismatch")
        return cls(opcode, request_id, payload, flags, version)


MAX_BATCH_COMMANDS = 256
_BATCH_HEADER = struct.Struct("<H")


@dataclass(frozen=True)
class CommandBatch:
    """Ordered collection of device commands carried as one transport unit."""

    commands: tuple[DeviceCommand, ...]

    def __post_init__(self) -> None:
        if len(self.commands) > MAX_BATCH_COMMANDS:
            raise ValueError("command batch is too large")
        if any(not isinstance(command, DeviceCommand) for command in self.commands):
            raise TypeError("command batch contains a non-command item")

    def encode(self) -> bytes:
        encoded = [command.encode() for command in self.commands]
        parts = [_BATCH_HEADER.pack(len(encoded))]
        for frame in encoded:
            if len(frame) > 0xFFFFFFFF:
                raise ValueError("command frame is too large")
            parts.append(struct.pack("<I", len(frame)))
            parts.append(frame)
        return b"".join(parts)

    @classmethod
    def decode(cls, payload: bytes) -> "CommandBatch":
        if len(payload) < _BATCH_HEADER.size:
            raise ValueError("Coreless command batch is truncated")
        count = _BATCH_HEADER.unpack(payload[:_BATCH_HEADER.size])[0]
        if count > MAX_BATCH_COMMANDS:
            raise ValueError("Coreless command batch is too large")
        offset = _BATCH_HEADER.size
        commands = []
        for _ in range(count):
            if len(payload) - offset < 4:
                raise ValueError("Coreless command batch frame length is truncated")
            length = struct.unpack("<I", payload[offset:offset + 4])[0]
            offset += 4
            end = offset + length
            if end > len(payload):
                raise ValueError("Coreless command batch frame is truncated")
            commands.append(DeviceCommand.decode(payload[offset:end]))
            offset = end
        if offset != len(payload):
            raise ValueError("Coreless command batch has trailing bytes")
        return cls(tuple(commands))

    def round_trip(self) -> "CommandBatch":
        """Encode and decode the batch at the transport boundary."""
        return type(self).decode(self.encode())


def batch_responses(
    batch: CommandBatch,
    payloads: tuple[bytes, ...] = (),
    *,
    errors: tuple[bool, ...] = (),
) -> CommandBatch:
    """Build correlated responses for every command in an ordered batch."""
    if payloads and len(payloads) != len(batch.commands):
        raise ValueError("batch payload count does not match command count")
    if errors and len(errors) != len(batch.commands):
        raise ValueError("batch error count does not match command count")
    values = payloads or (b"",) * len(batch.commands)
    flags = errors or (False,) * len(batch.commands)
    return CommandBatch(
        tuple(
            response(command, payload, error=error)
            for command, payload, error in zip(batch.commands, values, flags)
        )
    )

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

    
def encode_storage_write(key: str, data: bytes = b"") -> bytes:
    """Encode a deterministic UTF-8 storage key followed by its value bytes."""
    encoded_key = key.encode("utf-8")
    if not encoded_key:
        raise ValueError("storage key must not be empty")
    if len(encoded_key) > 0xFFFF:
        raise ValueError("storage key is too long")
    return struct.pack("<H", len(encoded_key)) + encoded_key + bytes(data)


def decode_storage_write(payload: bytes) -> tuple[str, bytes]:
    """Decode a storage-write payload into its key and value."""
    if len(payload) < 2:
        raise ValueError("storage write is missing key length")
    key_length = struct.unpack("<H", payload[:2])[0]
    key_end = 2 + key_length
    if key_length == 0:
        raise ValueError("storage key must not be empty")
    if key_end > len(payload):
        raise ValueError("storage write key is truncated")
    try:
        key = payload[2:key_end].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("storage write key is not valid UTF-8") from exc
    return key, bytes(payload[key_end:])
