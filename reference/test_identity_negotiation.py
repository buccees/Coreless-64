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


def test_identity_attach_exposes_only_capabilities_shared_with_host():
    interface = CorelessHostInterface(
        CorelessIdentity("coreless-shared"),
        supported={"display", "input", "network", "startup"},
    )
    frame = DeviceIdentityFrame(
        protocol_version=1,
        architecture=ARCHITECTURE_CORELESS64,
        device_type=DEVICE_TYPE_CORELESS64,
        capabilities=capability_bits({"display", "input", "network"}),
        payload=b"coreless-shared",
    ).encode()

    negotiated = interface.attach_identity_frame(
        frame,
        HostCapabilities(display=True, network=True),
    )

    assert negotiated == frozenset({"display", "network"})
    assert interface.negotiated == frozenset({"display", "network"})
    assert interface.supported == frozenset(
        {"display", "input", "network", "startup"}
    )


def test_identity_attach_detach_clears_transport_session_state():
    interface = CorelessHostInterface(
        CorelessIdentity("coreless-detach"),
        supported={"display", "input"},
    )
    frame = interface.device_identity_frame().encode()

    assert interface.attach_identity_frame(
        frame,
        HostCapabilities(display=True, input=True),
    ) == frozenset({"display", "input"})
    interface.bind_channel("display", object())

    interface.detach()

    assert not interface.attached
    assert interface.negotiated == frozenset()
    assert interface.channels == {}
    assert interface.required_channels(set()) == frozenset()


def test_identity_detach_allows_clean_reattach_with_fresh_negotiation():
    interface = CorelessHostInterface(
        CorelessIdentity("coreless-reattach"),
        supported={"display", "input"},
    )
    frame = interface.device_identity_frame().encode()

    assert interface.attach_identity_frame(
        frame,
        HostCapabilities(display=True, input=True),
    ) == frozenset({"display", "input"})
    interface.bind_channel("display", object())
    interface.detach()

    assert interface.attach_identity_frame(
        frame,
        HostCapabilities(display=True),
    ) == frozenset({"display"})
    assert interface.attached
    assert interface.negotiated == frozenset({"display"})
    assert interface.channels == {}
    assert interface.required_channels({"display"}) == frozenset({"display"})


def test_identity_failed_reattach_preserves_current_attachment_state():
    interface = CorelessHostInterface(
        CorelessIdentity("coreless-stable"),
        supported={"display", "input"},
    )
    valid = interface.device_identity_frame().encode()
    invalid = DeviceIdentityFrame(
        protocol_version=1,
        architecture=ARCHITECTURE_CORELESS64,
        device_type=DEVICE_TYPE_CORELESS64,
        capabilities=capability_bits({"display"}),
        payload=b"wrong-device",
    ).encode()

    assert interface.attach_identity_frame(
        valid,
        HostCapabilities(display=True, input=True),
    ) == frozenset({"display", "input"})
    channel = object()
    interface.bind_channel("display", channel)

    with pytest.raises(ValueError, match="transport identity verification failed"):
        interface.attach_identity_frame(invalid, HostCapabilities(display=True))

    assert interface.attached
    assert interface.negotiated == frozenset({"display", "input"})
    assert interface.channel("display") is channel
    assert interface.required_channels({"display"}) == frozenset()
    assert interface.required_channels({"input"}) == frozenset({"input"})


def test_identity_verification_rejects_wrong_transport_architecture():
    interface = CorelessHostInterface(CorelessIdentity("coreless-architecture"))
    frame = DeviceIdentityFrame(
        protocol_version=1,
        architecture=ARCHITECTURE_CORELESS64 + 1,
        device_type=DEVICE_TYPE_CORELESS64,
        capabilities=capability_bits({"display"}),
        payload=b"coreless-architecture",
    )

    assert not interface.verify_identity_frame(frame)


def test_identity_attach_rejects_non_utf8_identity_payload():
    interface = CorelessHostInterface(CorelessIdentity("coreless-payload"))
    frame = DeviceIdentityFrame(
        protocol_version=1,
        architecture=ARCHITECTURE_CORELESS64,
        device_type=DEVICE_TYPE_CORELESS64,
        capabilities=capability_bits({"display"}),
        payload=b"\xff",
    ).encode()

    with pytest.raises(ValueError, match="transport identity verification failed"):
        interface.attach_identity_frame(frame, HostCapabilities(display=True))
