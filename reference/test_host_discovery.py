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
from host_discovery import HostDeviceEnumerator, HostDiscoveryCandidate


def identity_frame(computer_id="coreless-a", capabilities=("display", "input")):
    return DeviceIdentityFrame(
        protocol_version=1,
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


def test_host_device_enumerator_rejects_duplicate_endpoint_ids():
    candidate = HostDiscoveryCandidate(
        "duplicate", identity_frame("one"), HostCapabilities()
    )
    with pytest.raises(ValueError, match="duplicate host endpoint id"):
        HostDeviceEnumerator().discover([candidate, candidate])


def test_host_device_enumerator_rejects_empty_endpoint_id():
    with pytest.raises(ValueError, match="endpoint_id must not be empty"):
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
    from host_discovery import HostDiscoveryProvider

    class Provider:
        def enumerate_candidates(self):
            return [
                HostDiscoveryCandidate("z", identity_frame("z"), HostCapabilities()),
                HostDiscoveryCandidate("a", identity_frame("a"), HostCapabilities()),
            ]

    provider = Provider()
    endpoints = HostDeviceEnumerator().discover_provider(provider)
    assert [endpoint.endpoint_id for endpoint in endpoints] == ["a", "z"]
