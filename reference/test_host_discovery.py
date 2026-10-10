import sys
sys.path.insert(0, ".")

import pytest

from device_protocol import (
    ARCHITECTURE_CORELESS64,
    DEVICE_TYPE_CORELESS64,
    DeviceIdentityFrame,
    capability_bits,
)
from host_interface import CorelessIdentity, CorelessHostInterface, HostCapabilities
from host_transport import HostEndpoint
from host_discovery import (
    HostDeviceEnumerator,
    HostDiscoveryCandidate,
    MemoryHostDiscoveryProvider,
)


def identity_frame(computer_id="coreless-a", capabilities=("display", "input"), protocol_version=1):
    return DeviceIdentityFrame(
        protocol_version=protocol_version,
        architecture=ARCHITECTURE_CORELESS64,
        device_type=DEVICE_TYPE_CORELESS64,
        capabilities=capability_bits(set(capabilities)),
        payload=computer_id.encode(),
    )


def test_host_device_enumerator_discovers_and_sorts_endpoints():
    candidates = [
        HostDiscoveryCandidate("b", identity_frame("coreless-b"), HostCapabilities(display=True)),
        HostDiscoveryCandidate("a", identity_frame("coreless-a"), HostCapabilities(input=True)),
    ]
    endpoints = HostDeviceEnumerator().discover(candidates)
    assert [endpoint.endpoint_id for endpoint in endpoints] == ["a", "b"]
    assert endpoints[0].identity == CorelessIdentity("coreless-a")
    assert endpoints[0].device_capabilities == frozenset({"display", "input"})


def test_host_device_enumerator_preserves_channels():
    channel = object()
    endpoint = HostDeviceEnumerator().discover(
        [HostDiscoveryCandidate(
            "coreless",
            identity_frame("coreless", ("network",)),
            HostCapabilities(network=True),
            {"network": channel},
        )]
    )[0]
    assert endpoint.channel_map()["network"] is channel


def test_host_device_enumerator_rejects_invalid_identity_frame():
    with pytest.raises(ValueError, match="invalid Coreless discovery identity frame"):
        HostDeviceEnumerator().discover(
            [HostDiscoveryCandidate("bad", b"not-coreless", HostCapabilities())]
        )


def test_host_device_enumerator_rejects_unsupported_protocol_version():
    candidate = HostDiscoveryCandidate(
        "future-version", identity_frame("future-version", protocol_version=2), HostCapabilities()
    )
    with pytest.raises(ValueError, match="unsupported Coreless discovery protocol version"):
        HostDeviceEnumerator().discover([candidate])


@pytest.mark.parametrize("endpoint_id", ["", "   ", None, 7])
def test_host_device_enumerator_rejects_invalid_endpoint_id_types(endpoint_id):
    candidate = HostDiscoveryCandidate(endpoint_id, identity_frame(), HostCapabilities())
    with pytest.raises(ValueError, match="endpoint_id must be a nonempty string"):
        HostDeviceEnumerator().discover([candidate])


def test_host_device_enumerator_rejects_non_frame_identity_objects():
    candidate = HostDiscoveryCandidate("bad-frame-object", object(), HostCapabilities())
    with pytest.raises(ValueError, match="invalid Coreless discovery identity frame"):
        HostDeviceEnumerator().discover([candidate])


def test_host_device_enumerator_rejects_invalid_host_capabilities_type():
    candidate = HostDiscoveryCandidate("bad-capabilities", identity_frame(), object())
    with pytest.raises(TypeError, match="host_capabilities must be HostCapabilities"):
        HostDeviceEnumerator().discover([candidate])



@pytest.mark.parametrize("channels", [[], "network", 7])
def test_host_device_enumerator_rejects_non_mapping_channels(channels):
    candidate = HostDiscoveryCandidate("bad-channels", identity_frame(), HostCapabilities(), channels)
    with pytest.raises(TypeError, match="channels must be a mapping or None"):
        HostDeviceEnumerator().discover([candidate])


@pytest.mark.parametrize("channels", [{None: object()}, {"": object()}, {7: object()}])
def test_host_device_enumerator_rejects_invalid_channel_names(channels):
    candidate = HostDiscoveryCandidate("bad-channel-name", identity_frame(), HostCapabilities(), channels)
    with pytest.raises(ValueError, match="discovery channel names must be nonempty strings"):
        HostDeviceEnumerator().discover([candidate])


def test_host_device_enumerator_rejects_none_channel_values():
    candidate = HostDiscoveryCandidate(
        "empty-channel", identity_frame("empty-channel", ("network",)),
        HostCapabilities(network=True), {"network": None}
    )
    with pytest.raises(ValueError, match="discovery channels must not be None"):
        HostDeviceEnumerator().discover([candidate])

def test_host_device_enumerator_rejects_duplicate_endpoint_ids():
    candidate = HostDiscoveryCandidate(
        "duplicate", identity_frame("one"), HostCapabilities()
    )
    with pytest.raises(ValueError, match="duplicate host endpoint id"):
        HostDeviceEnumerator().discover([candidate, candidate])


def test_host_device_enumerator_rejects_empty_endpoint_id():
    with pytest.raises(ValueError, match="endpoint_id must be a nonempty string"):
        HostDeviceEnumerator().discover(
            [HostDiscoveryCandidate("", identity_frame(), HostCapabilities())]
        )


def test_discovered_endpoint_uses_device_advertisement_for_connection():
    endpoint = HostDeviceEnumerator().discover(
        [HostDiscoveryCandidate(
            "coreless",
            identity_frame("coreless", ("display",)),
            HostCapabilities(display=True, input=True),
        )]
    )[0]
    interface = CorelessHostInterface(CorelessIdentity("coreless"))
    negotiated = interface.attach_identity_frame(
        endpoint.identity_frame(), endpoint.capabilities
    )
    assert negotiated == frozenset({"display"})


def test_host_device_enumerator_accepts_platform_provider():
    class Provider:
        def enumerate_candidates(self):
            return [
                HostDiscoveryCandidate("z", identity_frame("z"), HostCapabilities()),
                HostDiscoveryCandidate("a", identity_frame("a"), HostCapabilities()),
            ]

    provider = Provider()
    endpoints = HostDeviceEnumerator().discover_provider(provider)
    assert [endpoint.endpoint_id for endpoint in endpoints] == ["a", "z"]


def test_memory_host_discovery_provider_returns_stable_snapshot():
    candidates = [
        HostDiscoveryCandidate("a", identity_frame("a"), HostCapabilities()),
    ]
    provider = MemoryHostDiscoveryProvider(candidates)
    candidates.append(
        HostDiscoveryCandidate("b", identity_frame("b"), HostCapabilities())
    )

    assert [candidate.endpoint_id for candidate in provider.enumerate_candidates()] == ["a"]
    assert HostDeviceEnumerator().discover_provider(provider)[0].endpoint_id == "a"


def test_memory_host_discovery_provider_is_empty_by_default():
    provider = MemoryHostDiscoveryProvider()
    assert provider.enumerate_candidates() == ()
    assert HostDeviceEnumerator().discover_provider(provider) == ()


def test_host_device_enumerator_rejects_missing_advertised_network_channel():
    candidate = HostDiscoveryCandidate(
        "missing-network",
        identity_frame("missing-network", ("network",)),
        HostCapabilities(network=True),
    )
    with pytest.raises(ValueError, match="host discovery channels are missing"):
        HostDeviceEnumerator().discover([candidate])


def test_host_device_enumerator_accepts_advertised_network_channel():
    channel = object()
    candidate = HostDiscoveryCandidate(
        "network",
        identity_frame("network", ("network",)),
        HostCapabilities(network=True),
        {"network": channel},
    )
    endpoint = HostDeviceEnumerator().discover([candidate])[0]
    assert endpoint.channel_map()["network"] is channel


@pytest.mark.parametrize("frame", [
    DeviceIdentityFrame(
        protocol_version=1, architecture=ARCHITECTURE_CORELESS64,
        device_type=DEVICE_TYPE_CORELESS64, capabilities=0, payload="not-bytes"
    ),
    DeviceIdentityFrame(
        protocol_version=1, architecture=ARCHITECTURE_CORELESS64,
        device_type=DEVICE_TYPE_CORELESS64, capabilities=1 << 63, payload=b"bad"
    ),
    DeviceIdentityFrame(
        protocol_version=True, architecture=ARCHITECTURE_CORELESS64,
        device_type=DEVICE_TYPE_CORELESS64, capabilities=0, payload=b"bad"
    ),
])
def test_host_device_enumerator_validates_identity_frame_objects(frame):
    candidate = HostDiscoveryCandidate("invalid-frame-object", frame, HostCapabilities())
    with pytest.raises(ValueError, match="invalid Coreless discovery identity frame"):
        HostDeviceEnumerator().discover([candidate])
