import sys
sys.path.insert(0, ".")
import pytest
from host_interface import CorelessHostInterface, CorelessIdentity, HostCapabilities
from host_transport import HostEndpoint, MemoryHostTransportAdapter
from device_command import OP_CAPABILITIES, DeviceCommand, is_response

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


def test_host_transport_routes_commands_to_attached_coreless():
    endpoint = HostEndpoint(
        "coreless-command",
        CorelessIdentity("coreless-command"),
        HostCapabilities(display=True),
        device_capabilities={"display"},
    )
    adapter = MemoryHostTransportAdapter([endpoint])
    interface = CorelessHostInterface(CorelessIdentity("coreless-command"))
    reply = adapter.send_command(endpoint, interface, DeviceCommand(OP_CAPABILITIES, 17))
    assert is_response(reply)
    assert reply.request_id == 17
    assert reply.payload == b"display"


def test_host_transport_raw_exchange_returns_wire_response():
    endpoint = HostEndpoint(
        "coreless-wire",
        CorelessIdentity("coreless-wire"),
        HostCapabilities(display=True),
        device_capabilities={"display"},
    )
    adapter = MemoryHostTransportAdapter([endpoint])
    interface = CorelessHostInterface(CorelessIdentity("coreless-wire"))
    request = DeviceCommand(OP_CAPABILITIES, 21)
    reply_frame = adapter.exchange(endpoint, interface, request.encode())
    reply = DeviceCommand.decode(reply_frame)
    assert is_response(reply)
    assert reply.request_id == 21
    assert reply.payload == b"display"


def test_host_transport_command_path_reuses_existing_attachment():
    endpoint = HostEndpoint(
        "coreless-command-2",
        CorelessIdentity("coreless-command-2"),
        HostCapabilities(network=True),
        device_capabilities={"network"},
    )
    adapter = MemoryHostTransportAdapter([endpoint])
    interface = CorelessHostInterface(CorelessIdentity("coreless-command-2"))
    adapter.connect(endpoint, interface)
    reply = adapter.send_command(endpoint, interface, DeviceCommand(OP_CAPABILITIES, 18))
    assert reply.request_id == 18
    assert reply.payload == b"network"


def test_host_transport_disconnect_then_command_reattaches():
    endpoint = HostEndpoint(
        "coreless-lifecycle",
        CorelessIdentity("coreless-lifecycle"),
        HostCapabilities(display=True),
        device_capabilities={"display"},
    )
    adapter = MemoryHostTransportAdapter([endpoint])
    interface = CorelessHostInterface(CorelessIdentity("coreless-lifecycle"))
    adapter.connect(endpoint, interface)
    adapter.disconnect(interface)
    assert not interface.attached
    reply = adapter.send_command(endpoint, interface, DeviceCommand(OP_CAPABILITIES, 19))
    assert interface.attached
    assert reply.request_id == 19
    assert reply.payload == b"display"
