import sys
sys.path.insert(0, ".")
import pytest
from host_interface import CorelessHostInterface, CorelessIdentity, HostCapabilities
from host_transport import HostEndpoint, MemoryHostTransportAdapter

def test_host_transport_enumerates_endpoints_deterministically():
    adapter = MemoryHostTransportAdapter([
        HostEndpoint("b", CorelessIdentity("coreless-b"), HostCapabilities()),
        HostEndpoint("a", CorelessIdentity("coreless-a"), HostCapabilities()),
    ])
    assert [e.endpoint_id for e in adapter.enumerate()] == ["a", "b"]

def test_host_transport_identity_frame_drives_device_capability_negotiation():
    endpoint = HostEndpoint(
        "coreless-0",
        CorelessIdentity("coreless-0"),
        HostCapabilities(display=True, input=True),
        device_capabilities={"display", "input"},
    )
    interface = CorelessHostInterface(CorelessIdentity("coreless-0"))
    assert interface.attach_identity_frame(
        endpoint.identity_frame(), endpoint.capabilities
    ) == frozenset({"display", "input"})


def test_host_transport_connects_negotiated_channels():
    display = object()
    endpoint = HostEndpoint("coreless-0", CorelessIdentity("coreless-0"),
                            HostCapabilities(display=True, startup=True),
                            {"display": display})
    adapter = MemoryHostTransportAdapter([endpoint])
    interface = CorelessHostInterface(CorelessIdentity("coreless-0"))
    negotiated = adapter.connect(endpoint, interface)
    assert negotiated == frozenset({"display", "startup"})
    assert interface.channel("display") is display
    assert interface.transport_ready({"display"})

def test_host_transport_rejects_unknown_endpoint():
    endpoint = HostEndpoint("coreless-0", CorelessIdentity("coreless-0"), HostCapabilities())
    adapter = MemoryHostTransportAdapter()
    interface = CorelessHostInterface(CorelessIdentity("coreless-0"))
    with pytest.raises(ValueError, match="unknown host endpoint"):
        adapter.connect(endpoint, interface)
