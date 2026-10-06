"""Transport-neutral Coreless-64 plug-and-play identification protocol.

The frame is deliberately independent of USB, PCIe, SATA, NVMe, Ethernet, or
another physical link. A concrete adapter can carry this frame over whatever
transport the host and Coreless endpoint negotiate.
"""

from __future__ import annotations

from dataclasses import dataclass
import struct


MAGIC = b"CORELS64"
PROTOCOL_VERSION = 1
FRAME_TYPE_IDENTITY = 1
ARCHITECTURE_CORELESS64 = 1

_HEADER = struct.Struct("<8sHHIIQII")
HEADER_SIZE = _HEADER.size


@dataclass(frozen=True)
class DeviceIdentityFrame:
    """Stable machine-readable identity advertised before higher-level services."""

    protocol_version: int
    architecture: int
    device_type: int
    capabilities: int
    payload: bytes = b""
    flags: int = 0

    def encode(self) -> bytes:
        if self.protocol_version <= 0:
            raise ValueError("protocol version must be positive")
        if self.architecture != ARCHITECTURE_CORELESS64:
            raise ValueError("unsupported Coreless architecture")
        if not 0 <= self.device_type <= 0xFFFFFFFF:
            raise ValueError("device type out of range")
        if not 0 <= self.capabilities <= 0xFFFFFFFFFFFFFFFF:
            raise ValueError("capability bits out of range")
        if not 0 <= self.flags <= 0xFFFFFFFF:
            raise ValueError("flags out of range")
        if len(self.payload) > 0xFFFFFFFF:
            raise ValueError("identity payload is too large")
        return _HEADER.pack(
            MAGIC,
            self.protocol_version,
            FRAME_TYPE_IDENTITY,
            self.architecture,
            self.device_type,
            self.capabilities,
            len(self.payload),
            self.flags,
        ) + self.payload

    @classmethod
    def decode(cls, frame: bytes) -> "DeviceIdentityFrame":
        if len(frame) < HEADER_SIZE:
            raise ValueError("Coreless identity frame is truncated")
        (
            magic,
            protocol_version,
            frame_type,
            architecture,
            device_type,
            capabilities,
            payload_length,
            flags,
        ) = _HEADER.unpack(frame[:HEADER_SIZE])
        if magic != MAGIC:
            raise ValueError("invalid Coreless identity magic")
        if frame_type != FRAME_TYPE_IDENTITY:
            raise ValueError("unsupported Coreless frame type")
        payload = frame[HEADER_SIZE:]
        if len(payload) != payload_length:
            raise ValueError("Coreless identity payload length mismatch")
        if architecture != ARCHITECTURE_CORELESS64:
            raise ValueError("unsupported Coreless architecture")
        return cls(
            protocol_version=protocol_version,
            architecture=architecture,
            device_type=device_type,
            capabilities=capabilities,
            payload=payload,
            flags=flags,
        )


def capability_bits(names: set[str] | frozenset[str]) -> int:
    """Encode named Coreless capabilities into a stable bitset."""
    known = {
        "compute": 0,
        "vector": 1,
        "matrix": 2,
        "ai": 3,
        "storage": 4,
        "network": 5,
        "display": 6,
        "input": 7,
        "management": 8,
    }
    bits = 0
    for name in names:
        if name not in known:
            raise ValueError(f"unknown Coreless capability: {name}")
        bits |= 1 << known[name]
    return bits
