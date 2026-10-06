import sys
sys.path.insert(0, ".")

import pytest

from device_protocol import (
    ARCHITECTURE_CORELESS64,
    HEADER_SIZE,
    MAGIC,
    DeviceIdentityFrame,
    capability_bits,
    capability_names,
)


def test_coreless_identity_frame_round_trips():
    frame = DeviceIdentityFrame(
        protocol_version=1,
        architecture=ARCHITECTURE_CORELESS64,
        device_type=1,
        capabilities=capability_bits({"compute", "vector", "matrix", "ai"}),
        payload=b"coreless-0",
        flags=3,
    )

    encoded = frame.encode()
    decoded = DeviceIdentityFrame.decode(encoded)

    assert encoded.startswith(MAGIC)
    assert len(encoded) == HEADER_SIZE + len(frame.payload)
    assert decoded == frame


def test_coreless_identity_frame_rejects_non_coreless_magic():
    frame = bytearray(
        DeviceIdentityFrame(
            protocol_version=1,
            architecture=ARCHITECTURE_CORELESS64,
            device_type=1,
            capabilities=0,
        ).encode()
    )
    frame[:8] = b"NOTCORE!"

    with pytest.raises(ValueError, match="magic"):
        DeviceIdentityFrame.decode(bytes(frame))


def test_coreless_identity_frame_rejects_truncated_payload():
    encoded = DeviceIdentityFrame(
        protocol_version=1,
        architecture=ARCHITECTURE_CORELESS64,
        device_type=1,
        capabilities=0,
        payload=b"coreless",
    ).encode()

    with pytest.raises(ValueError, match="payload length"):
        DeviceIdentityFrame.decode(encoded[:-1])


def test_coreless_capability_bits_are_stable():
    bits = capability_bits(frozenset({"compute", "vector", "matrix", "ai"}))
    assert bits == (1 << 0) | (1 << 1) | (1 << 2) | (1 << 3)


def test_coreless_capability_bits_reject_unknown_names():
    with pytest.raises(ValueError, match="unknown Coreless capability"):
        capability_bits({"compute", "not-a-capability"})


def test_coreless_capability_bits_decode_for_discovery():
    bits = capability_bits(frozenset({"compute", "storage", "network", "display"}))
    assert capability_names(bits) == frozenset({"compute", "storage", "network", "display"})


def test_coreless_capability_bits_reject_unknown_bits():
    with pytest.raises(ValueError, match="unknown Coreless capability bits"):
        capability_names(1 << 63)
