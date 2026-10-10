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
DEVICE_TYPE_CORELESS64 = 1
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
        for name, value in (
            ("protocol_version", self.protocol_version),
            ("architecture", self.architecture),
            ("device_type", self.device_type),
            ("capabilities", self.capabilities),
            ("flags", self.flags),
        ):
            if type(value) is not int:
                raise TypeError(f"{name} must be an integer")
        if not 1 <= self.protocol_version <= 0xFFFF:
            raise ValueError("protocol version out of range")
        if self.architecture != ARCHITECTURE_CORELESS64:
            raise ValueError("unsupported Coreless architecture")
        if not 0 <= self.device_type <= 0xFFFFFFFF:
            raise ValueError("device type out of range")
        if not 0 <= self.capabilities <= 0xFFFFFFFFFFFFFFFF:
            raise ValueError("capability bits out of range")
        if not 0 <= self.flags <= 0xFFFFFFFF:
            raise ValueError("flags out of range")
        if not isinstance(self.payload, (bytes, bytearray, memoryview)):
            raise TypeError("identity payload must be bytes-like")
        payload = bytes(self.payload)
        if len(payload) > 0xFFFFFFFF:
            raise ValueError("identity payload is too large")
        # Reject unknown bits before a frame can be emitted onto a transport.
        capability_names(self.capabilities)
        return _HEADER.pack(MAGIC, self.protocol_version, FRAME_TYPE_IDENTITY,
                            self.architecture, self.device_type, self.capabilities,
                            len(payload), self.flags) + payload

    def capability_names(self) -> frozenset[str]:
        return capability_names(self.capabilities)

    def capability_mask(self, names: set[str] | frozenset[str]) -> int:
        """Return the wire bit mask for a selected set of advertised capabilities."""
        return self.capabilities & capability_bits(names)

    def is_coreless64(self) -> bool:
        return self.architecture == ARCHITECTURE_CORELESS64 and self.device_type == DEVICE_TYPE_CORELESS64

    @classmethod
    def decode(cls, frame: bytes) -> "DeviceIdentityFrame":
        if not isinstance(frame, (bytes, bytearray, memoryview)):
            raise TypeError("Coreless identity frame must be bytes-like")
        frame = bytes(frame)
        if len(frame) < HEADER_SIZE:
            raise ValueError("Coreless identity frame is truncated")
        magic, protocol_version, frame_type, architecture, device_type, capabilities, payload_length, flags = _HEADER.unpack(frame[:HEADER_SIZE])
        if magic != MAGIC:
            raise ValueError("invalid Coreless identity magic")
        if frame_type != FRAME_TYPE_IDENTITY:
            raise ValueError("unsupported Coreless frame type")
        payload = frame[HEADER_SIZE:]
        if len(payload) != payload_length:
            raise ValueError("Coreless identity payload length mismatch")
        if architecture != ARCHITECTURE_CORELESS64:
            raise ValueError("unsupported Coreless architecture")
        if device_type != DEVICE_TYPE_CORELESS64:
            raise ValueError("unsupported Coreless device type")
        capability_names(capabilities)
        return cls(protocol_version, architecture, device_type, capabilities, payload, flags)

_CAPABILITIES = {"compute": 0, "vector": 1, "matrix": 2, "ai": 3, "storage": 4, "network": 5, "display": 6, "input": 7, "management": 8, "startup": 9, "telemetry": 10}

def capability_names(bits: int) -> frozenset[str]:
    if not 0 <= bits <= 0xFFFFFFFFFFFFFFFF:
        raise ValueError("capability bits out of range")
    known_mask = sum(1 << bit for bit in _CAPABILITIES.values())
    if bits & ~known_mask:
        raise ValueError("unknown Coreless capability bits")
    return frozenset(name for name, bit in _CAPABILITIES.items() if bits & (1 << bit))

def capability_bits(names: set[str] | frozenset[str]) -> int:
    bits = 0
    for name in names:
        if name not in _CAPABILITIES:
            raise ValueError(f"unknown Coreless capability: {name}")
        bits |= 1 << _CAPABILITIES[name]
    return bits
