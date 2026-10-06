import sys
sys.path.insert(0, ".")

import pytest

from device_protocol import (
    ARCHITECTURE_CORELESS64,
    DEVICE_TYPE_CORELESS64,
    DeviceIdentityFrame,
    capability_bits,
)
from host_interface import CorelessHostInterface, CorelessIdentity, HostCapabilities


def test_identity_attach_negotiate_is_limited_by_device_advertisement():
    interface = CorelessHostInterface(
        CorelessIdentity("coreless-filter"),
        supported={"display", "input", "network", "startup"},
    )
    original_supported = interface.supported
    frame = DeviceIdentityFrame(
        protocol_version=1,
        architecture=ARCHITECTURE_CORELESS64,
        device_type=DEVICE_TYPE_CORELESS64,
        capabilities=capability_bits({"display", "startup"}),
        payload=b"coreless-filter",
    ).encode()

    negotiated = interface.attach_identity_frame(
        frame,
        HostCapabilities(display=True, input=True, network=True, startup=True),
    )

    assert negotiated == frozenset({"display", "startup"})
    assert interface.negotiated == frozenset({"display", "startup"})
    assert interface.supported == original_supported


def test_identity_attach_rejects_protocol_version_mismatch():
    interface = CorelessHostInterface(CorelessIdentity("coreless-version"))
    frame = DeviceIdentityFrame(
        protocol_version=2,
        architecture=ARCHITECTURE_CORELESS64,
        device_type=DEVICE_TYPE_CORELESS64,
        capabilities=capability_bits({"display"}),
        payload=b"coreless-version",
    ).encode()

    with pytest.raises(ValueError, match="transport identity verification failed"):
        interface.attach_identity_frame(frame, HostCapabilities(display=True))


def test_identity_attach_can_refresh_negotiation_without_shrinking_device_capabilities():
    interface = CorelessHostInterface(
        CorelessIdentity("coreless-refresh"),
        supported={"display", "input", "network", "startup"},
    )
    original_supported = interface.supported

    display_frame = DeviceIdentityFrame(
        protocol_version=1,
        architecture=ARCHITECTURE_CORELESS64,
        device_type=DEVICE_TYPE_CORELESS64,
        capabilities=capability_bits({"display"}),
        payload=b"coreless-refresh",
    ).encode()
    input_frame = DeviceIdentityFrame(
        protocol_version=1,
        architecture=ARCHITECTURE_CORELESS64,
        device_type=DEVICE_TYPE_CORELESS64,
        capabilities=capability_bits({"input"}),
        payload=b"coreless-refresh",
    ).encode()

    assert interface.attach_identity_frame(
        display_frame,
        HostCapabilities(display=True, input=True),
    ) == frozenset({"display"})
    assert interface.supported == original_supported

    assert interface.attach_identity_frame(
        input_frame,
        HostCapabilities(display=True, input=True),
    ) == frozenset({"input"})
    assert interface.negotiated == frozenset({"input"})
    assert interface.supported == original_supported


def test_identity_attach_rejects_unknown_advertised_capability_bits():
    interface = CorelessHostInterface(CorelessIdentity("coreless-invalid"))
    frame = DeviceIdentityFrame(
        protocol_version=1,
        architecture=ARCHITECTURE_CORELESS64,
        device_type=DEVICE_TYPE_CORELESS64,
        capabilities=1 << 63,
        payload=b"coreless-invalid",
    ).encode()

    with pytest.raises(ValueError, match="unknown Coreless capability bits"):
        interface.attach_identity_frame(frame, HostCapabilities(display=True))
