import sys
sys.path.insert(0, ".")
import pytest
from host_interface import CorelessHostInterface, CorelessIdentity, HostCapabilities
from host_transport import HostEndpoint, MemoryHostTransportAdapter
from device_command import OP_CAPABILITIES, OP_STATUS, OP_SYNC, DeviceCommand, is_response


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
    endpoint = HostEndpoint(
        "coreless-0",
        CorelessIdentity("coreless-0"),
        HostCapabilities(display=True, startup=True),
        {"display": display},
    )
    adapter = MemoryHostTransportAdapter([endpoint])
    interface = CorelessHostInterface(CorelessIdentity("coreless-0"))
    negotiated = adapter.connect(endpoint, interface)
    assert negotiated == frozenset({"display", "startup"})
    assert interface.channel("display") is display
    assert interface.transport_ready({"display"})


def test_host_transport_rejects_invalid_host_io_before_attachment():
    endpoint = HostEndpoint(
        "coreless-invalid-io",
        CorelessIdentity("coreless-invalid-io"),
        HostCapabilities(display=True),
        device_capabilities={"display"},
    )
    adapter = MemoryHostTransportAdapter([endpoint])
    interface = CorelessHostInterface(CorelessIdentity("coreless-invalid-io"))
    with pytest.raises(TypeError, match="HostIO contract"):
        adapter.connect(endpoint, interface, host_io=object())
    assert not interface.attached


def test_host_transport_rejects_unknown_endpoint():
    endpoint = HostEndpoint(
        "coreless-0", CorelessIdentity("coreless-0"), HostCapabilities()
    )
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
    reply = adapter.send_command(
        endpoint, interface, DeviceCommand(OP_CAPABILITIES, 17)
    )
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
    reply = adapter.send_command(
        endpoint, interface, DeviceCommand(OP_CAPABILITIES, 18)
    )
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
    reply = adapter.send_command(
        endpoint, interface, DeviceCommand(OP_CAPABILITIES, 19)
    )
    assert interface.attached
    assert reply.request_id == 19
    assert reply.payload == b"display"


def test_host_transport_rejects_attached_interface_for_other_endpoint():
    endpoint_a = HostEndpoint(
        "coreless-identity-a",
        CorelessIdentity("coreless-identity-a"),
        HostCapabilities(display=True),
        device_capabilities={"display"},
    )
    endpoint_b = HostEndpoint(
        "coreless-identity-b",
        CorelessIdentity("coreless-identity-b"),
        HostCapabilities(display=True),
        device_capabilities={"display"},
    )
    adapter = MemoryHostTransportAdapter([endpoint_a, endpoint_b])
    interface = CorelessHostInterface(CorelessIdentity("coreless-identity-a"))
    adapter.connect(endpoint_a, interface)

    with pytest.raises(ValueError, match="identity mismatch"):
        adapter.exchange(
            endpoint_b,
            interface,
            DeviceCommand(OP_CAPABILITIES, 20).encode(),
        )


def test_host_transport_session_reuses_negotiated_attachment():
    endpoint = HostEndpoint(
        "coreless-session",
        CorelessIdentity("coreless-session"),
        HostCapabilities(display=True, network=True),
        device_capabilities={"display", "network"},
    )
    adapter = MemoryHostTransportAdapter([endpoint])
    interface = CorelessHostInterface(CorelessIdentity("coreless-session"))
    session = adapter.open_session(endpoint, interface)
    assert session.endpoint_id == "coreless-session"
    assert session.endpoint is endpoint
    assert session.negotiated == frozenset({"display", "network"})
    reply = adapter.send_session_command(
        session, DeviceCommand(OP_CAPABILITIES, 31)
    )
    assert reply.request_id == 31
    assert reply.payload == b"display|network"
    adapter.close_session(session)
    assert not session.attached


def test_host_transport_session_keeps_bound_endpoint_after_enumeration_change():
    endpoint = HostEndpoint(
        "coreless-session-stable",
        CorelessIdentity("coreless-session-stable"),
        HostCapabilities(display=True),
        device_capabilities={"display"},
    )
    adapter = MemoryHostTransportAdapter([endpoint])
    interface = CorelessHostInterface(CorelessIdentity("coreless-session-stable"))
    session = adapter.open_session(endpoint, interface)
    adapter.unregister(endpoint.endpoint_id)

    reply = adapter.send_session_command(
        session, DeviceCommand(OP_CAPABILITIES, 32)
    )
    assert reply.request_id == 32
    assert reply.payload == b"display"


def test_host_transport_session_rejects_rebound_interface():
    endpoint_a = HostEndpoint(
        "coreless-session-a",
        CorelessIdentity("coreless-session-a"),
        HostCapabilities(display=True),
        device_capabilities={"display"},
    )
    endpoint_b = HostEndpoint(
        "coreless-session-b",
        CorelessIdentity("coreless-session-b"),
        HostCapabilities(network=True),
        device_capabilities={"network"},
    )
    adapter = MemoryHostTransportAdapter([endpoint_a, endpoint_b])
    interface = CorelessHostInterface(CorelessIdentity("coreless-session-a"))
    session = adapter.open_session(endpoint_a, interface)

    adapter.disconnect(interface)

    with pytest.raises(ValueError, match="identity verification failed"):
        adapter.connect(endpoint_b, interface)

    with pytest.raises(RuntimeError, match="host transport session is detached"):
        adapter.send_session_command(
            session, DeviceCommand(OP_CAPABILITIES, 33)
        )


def test_host_transport_session_rejects_negotiation_change():
    endpoint = HostEndpoint(
        "coreless-session-negotiation",
        CorelessIdentity("coreless-session-negotiation"),
        HostCapabilities(display=True, network=True),
        device_capabilities={"display", "network"},
    )
    adapter = MemoryHostTransportAdapter([endpoint])
    interface = CorelessHostInterface(CorelessIdentity("coreless-session-negotiation"))
    session = adapter.open_session(endpoint, interface)

    adapter.disconnect(interface)
    adapter.connect(
        endpoint,
        interface,
    )

    assert session.negotiated == frozenset({"display", "network"})
    reply = adapter.send_session_command(
        session, DeviceCommand(OP_CAPABILITIES, 34)
    )
    assert reply.request_id == 34


def test_host_transport_session_rejects_non_response_frame(monkeypatch):
    endpoint = HostEndpoint(
        "coreless-session-response",
        CorelessIdentity("coreless-session-response"),
        HostCapabilities(display=True),
        device_capabilities={"display"},
    )
    adapter = MemoryHostTransportAdapter([endpoint])
    interface = CorelessHostInterface(CorelessIdentity("coreless-session-response"))
    session = adapter.open_session(endpoint, interface)
    monkeypatch.setattr(
        adapter,
        "exchange_session",
        lambda _session, _frame: DeviceCommand(OP_CAPABILITIES, 41).encode(),
    )
    with pytest.raises(ValueError, match="not a response frame"):
        adapter.send_session_command(session, DeviceCommand(OP_CAPABILITIES, 41))


def test_host_transport_session_rejects_correlation_mismatch(monkeypatch):
    endpoint = HostEndpoint(
        "coreless-session-correlation",
        CorelessIdentity("coreless-session-correlation"),
        HostCapabilities(display=True),
        device_capabilities={"display"},
    )
    adapter = MemoryHostTransportAdapter([endpoint])
    interface = CorelessHostInterface(CorelessIdentity("coreless-session-correlation"))
    session = adapter.open_session(endpoint, interface)
    monkeypatch.setattr(
        adapter,
        "exchange_session",
        lambda _session, _frame: DeviceCommand(OP_CAPABILITIES, 999, b"bad", flags=1).encode(),
    )
    with pytest.raises(ValueError, match="request id mismatch"):
        adapter.send_session_command(session, DeviceCommand(OP_CAPABILITIES, 42))


def test_host_transport_direct_command_rejects_non_response(monkeypatch):
    endpoint = HostEndpoint(
        "coreless-direct-response",
        CorelessIdentity("coreless-direct-response"),
        HostCapabilities(display=True),
        device_capabilities={"display"},
    )
    adapter = MemoryHostTransportAdapter([endpoint])
    interface = CorelessHostInterface(CorelessIdentity("coreless-direct-response"))
    monkeypatch.setattr(
        adapter,
        "exchange",
        lambda _endpoint, _interface, _frame: DeviceCommand(OP_CAPABILITIES, 7).encode(),
    )
    with pytest.raises(ValueError, match="not a response frame"):
        adapter.send_command(endpoint, interface, DeviceCommand(OP_CAPABILITIES, 7))


def test_host_transport_direct_command_rejects_opcode_mismatch(monkeypatch):
    endpoint = HostEndpoint(
        "coreless-direct-opcode",
        CorelessIdentity("coreless-direct-opcode"),
        HostCapabilities(display=True),
        device_capabilities={"display"},
    )
    adapter = MemoryHostTransportAdapter([endpoint])
    interface = CorelessHostInterface(CorelessIdentity("coreless-direct-opcode"))
    monkeypatch.setattr(
        adapter,
        "exchange",
        lambda _endpoint, _interface, _frame: DeviceCommand(OP_STATUS, 7, flags=1).encode(),
    )
    with pytest.raises(ValueError, match="opcode mismatch"):
        adapter.send_command(endpoint, interface, DeviceCommand(OP_CAPABILITIES, 7))


def test_host_transport_sync_persists_bound_system(monkeypatch):
    from system import CorelessSystem
    endpoint = HostEndpoint(
        "coreless-sync",
        CorelessIdentity("coreless-sync"),
        HostCapabilities(display=True),
        device_capabilities={"display"},
    )
    adapter = MemoryHostTransportAdapter([endpoint])
    interface = CorelessHostInterface(CorelessIdentity("coreless-sync"))
    system = CorelessSystem(memory_size=128 * 1024)
    adapter.connect(endpoint, interface)
    interface.attach_system(system)
    calls = []
    monkeypatch.setattr(system.machine, "save_state", lambda: calls.append("saved"))
    reply = adapter.send_command(endpoint, interface, DeviceCommand(OP_SYNC, 55))
    assert reply.request_id == 55
    assert reply.payload == b"ok"
    assert calls == ["saved"]

    
def test_host_transport_reconnect_drops_stale_channels():
    display = object()
    endpoint = HostEndpoint(
        "coreless-channel-refresh",
        CorelessIdentity("coreless-channel-refresh"),
        HostCapabilities(display=True, network=True),
        {"display": display, "network": object()},
        device_capabilities={"display", "network"},
    )
    adapter = MemoryHostTransportAdapter([endpoint])
    interface = CorelessHostInterface(CorelessIdentity("coreless-channel-refresh"))
    adapter.connect(endpoint, interface)
    assert interface.channel("display") is display

    refreshed = HostEndpoint(
        "coreless-channel-refresh",
        CorelessIdentity("coreless-channel-refresh"),
        HostCapabilities(display=True),
        {"display": display},
        device_capabilities={"display"},
    )
    adapter.register(refreshed)
    adapter.connect(refreshed, interface)

    assert interface.transport_ready({"display"})
    with pytest.raises(KeyError, match="no channel bound: network"):
        interface.channel("network")


def test_host_transport_session_exposes_and_requires_live_channels():
    display = object()
    endpoint = HostEndpoint(
        "coreless-session-channels",
        CorelessIdentity("coreless-session-channels"),
        HostCapabilities(display=True),
        {"display": display},
        device_capabilities={"display"},
    )
    adapter = MemoryHostTransportAdapter([endpoint])
    interface = CorelessHostInterface(CorelessIdentity("coreless-session-channels"))
    session = adapter.open_session(endpoint, interface)

    assert session.channel("display") is display
    session.require_channels({"display"})

    adapter.disconnect(interface)
    with pytest.raises(RuntimeError, match="session is detached"):
        session.require_channels({"display"})


def test_host_transport_sends_ordered_command_batch():
    from device_command import CommandBatch
    endpoint = HostEndpoint(
        "coreless-batch",
        CorelessIdentity("coreless-batch"),
        HostCapabilities(display=True),
        device_capabilities={"display"},
    )
    adapter = MemoryHostTransportAdapter([endpoint])
    interface = CorelessHostInterface(CorelessIdentity("coreless-batch"))
    batch = CommandBatch((
        DeviceCommand(OP_CAPABILITIES, 60),
        DeviceCommand(OP_STATUS, 61),
    ))
    reply = adapter.send_batch(endpoint, interface, batch)
    assert [command.request_id for command in reply.commands] == [60, 61]
    assert reply.commands[0].payload == b"display"
    assert reply.commands[1].flags & 1


def test_host_transport_session_sends_ordered_command_batch():
    from device_command import CommandBatch
    endpoint = HostEndpoint(
        "coreless-session-batch",
        CorelessIdentity("coreless-session-batch"),
        HostCapabilities(display=True),
        device_capabilities={"display"},
    )
    adapter = MemoryHostTransportAdapter([endpoint])
    interface = CorelessHostInterface(CorelessIdentity("coreless-session-batch"))
    session = adapter.open_session(endpoint, interface)
    batch = CommandBatch((
        DeviceCommand(OP_CAPABILITIES, 62),
        DeviceCommand(OP_STATUS, 63),
    ))
    reply = adapter.send_session_batch(session, batch)
    assert [command.request_id for command in reply.commands] == [62, 63]
    assert reply.commands[0].payload == b"display"


def test_host_transport_batch_rejects_response_count_mismatch(monkeypatch):
    from device_command import CommandBatch
    endpoint = HostEndpoint(
        "coreless-batch-count",
        CorelessIdentity("coreless-batch-count"),
        HostCapabilities(display=True),
        device_capabilities={"display"},
    )
    adapter = MemoryHostTransportAdapter([endpoint])
    interface = CorelessHostInterface(CorelessIdentity("coreless-batch-count"))
    monkeypatch.setattr(
        adapter,
        "exchange_batch",
        lambda _endpoint, _interface, _payload: CommandBatch(
            (DeviceCommand(OP_CAPABILITIES, 70, flags=1),)
        ).encode(),
    )
    batch = CommandBatch((
        DeviceCommand(OP_CAPABILITIES, 70),
        DeviceCommand(OP_STATUS, 71),
    ))
    with pytest.raises(ValueError, match="response count mismatch"):
        adapter.send_batch(endpoint, interface, batch)


def test_provider_host_transport_adapter_enumerates_validated_endpoints():
    from device_protocol import (
        ARCHITECTURE_CORELESS64,
        DEVICE_TYPE_CORELESS64,
        DeviceIdentityFrame,
        capability_bits,
    )
    from host_discovery import HostDiscoveryCandidate

    class Provider:
        def enumerate_candidates(self):
            frame = DeviceIdentityFrame(
                protocol_version=1,
                architecture=ARCHITECTURE_CORELESS64,
                device_type=DEVICE_TYPE_CORELESS64,
                capabilities=capability_bits({"display"}),
                payload=b"provider",
            )
            return [
                HostDiscoveryCandidate(
                    "provider-endpoint",
                    frame,
                    HostCapabilities(display=True),
                )
            ]

    from host_transport import ProviderHostTransportAdapter

    adapter = ProviderHostTransportAdapter(Provider())
    endpoints = adapter.enumerate()
    assert [endpoint.endpoint_id for endpoint in endpoints] == ["provider-endpoint"]
    assert adapter.provider is not None


def test_host_transport_discovery_validates_raw_candidates():
    from device_protocol import ARCHITECTURE_CORELESS64, DEVICE_TYPE_CORELESS64, DeviceIdentityFrame, capability_bits
    from host_discovery import HostDiscoveryCandidate

    frame = DeviceIdentityFrame(
        protocol_version=1,
        architecture=ARCHITECTURE_CORELESS64,
        device_type=DEVICE_TYPE_CORELESS64,
        capabilities=capability_bits({"display"}),
        payload=b"discovered",
    )
    adapter = MemoryHostTransportAdapter(candidates=[
        HostDiscoveryCandidate("z", frame, HostCapabilities(display=True)),
        HostDiscoveryCandidate("a", frame, HostCapabilities(display=True)),
    ])
    assert [e.endpoint_id for e in adapter.enumerate_candidates()] == ["a", "z"]


def test_host_transport_discovery_rejects_duplicate_raw_candidates():
    from host_discovery import HostDiscoveryCandidate
    from device_protocol import ARCHITECTURE_CORELESS64, DEVICE_TYPE_CORELESS64, DeviceIdentityFrame

    frame = DeviceIdentityFrame(
        protocol_version=1,
        architecture=ARCHITECTURE_CORELESS64,
        device_type=DEVICE_TYPE_CORELESS64,
        capabilities=0,
        payload=b"duplicate",
    )
    candidate = HostDiscoveryCandidate("same", frame, HostCapabilities())
    adapter = MemoryHostTransportAdapter(candidates=[candidate, candidate])
    with pytest.raises(ValueError, match="duplicate host endpoint id"):
        adapter.enumerate_candidates()


def test_host_transport_discovers_from_platform_provider():
    from host_discovery import HostDiscoveryCandidate

    class Provider:
        def enumerate_candidates(self):
            return [
                HostDiscoveryCandidate(
                    "platform-a",
                    CorelessIdentity("platform-a").protocol_version and
                    HostEndpoint(
                        "platform-a",
                        CorelessIdentity("platform-a"),
                        HostCapabilities(display=True),
                        device_capabilities={"display"},
                    ).identity_frame(),
                    HostCapabilities(display=True),
                )
            ]

    adapter = MemoryHostTransportAdapter()
    endpoints = adapter.discover_provider(Provider())
    assert [endpoint.endpoint_id for endpoint in endpoints] == ["platform-a"]


def test_socket_host_transport_adapter_opens_network_channel():
    import socket
    from host_socket import SocketNetworkTransport
    from host_transport import SocketHostTransportAdapter

    left, right = socket.socketpair()
    endpoint = HostEndpoint(
        "socket-host",
        CorelessIdentity("socket-host"),
        HostCapabilities(network=True),
        {"network": left},
        device_capabilities={"network"},
    )
    adapter = SocketHostTransportAdapter(object())
    transport = adapter.open_network(endpoint)
    assert isinstance(transport, SocketNetworkTransport)
    transport.send_packet(b"coreless")
    assert right.recv(1024).endswith(b"coreless")
    transport.close()
    right.close()


def test_socket_host_transport_adapter_requires_network_channel():
    from host_transport import SocketHostTransportAdapter
    endpoint = HostEndpoint(
        "no-network-channel",
        CorelessIdentity("no-network-channel"),
        HostCapabilities(network=True),
        device_capabilities={"network"},
    )
    with pytest.raises(RuntimeError, match="no network channel"):
        SocketHostTransportAdapter(object()).open_network(endpoint)


def test_socket_host_transport_adapter_requires_network_capability():
    from host_transport import SocketHostTransportAdapter
    endpoint = HostEndpoint(
        "no-network-capability",
        CorelessIdentity("no-network-capability"),
        HostCapabilities(),
        {"network": object()},
        device_capabilities={"network"},
    )
    with pytest.raises(RuntimeError, match="does not advertise network capability"):
        SocketHostTransportAdapter(object()).open_network(endpoint)


def test_socket_host_transport_adapter_rejects_closed_channel():
    import socket
    from host_transport import SocketHostTransportAdapter

    left, right = socket.socketpair()
    left.close()
    endpoint = HostEndpoint(
        "closed-network",
        CorelessIdentity("closed-network"),
        HostCapabilities(network=True),
        {"network": left},
        device_capabilities={"network"},
    )
    try:
        with pytest.raises(RuntimeError, match="already closed"):
            SocketHostTransportAdapter(object()).open_network(endpoint)
    finally:
        right.close()


def test_socket_host_transport_session_binds_typed_network_transport():
    import socket
    from host_socket import SocketNetworkTransport
    from host_transport import SocketHostTransportAdapter

    left, right = socket.socketpair()
    endpoint = HostEndpoint(
        "socket-session",
        CorelessIdentity("socket-session"),
        HostCapabilities(network=True),
        {"network": left},
        device_capabilities={"network"},
    )
    adapter = SocketHostTransportAdapter(object())
    interface = CorelessHostInterface(CorelessIdentity("socket-session"))

    session = adapter.open_session(endpoint, interface)
    transport = session.channel("network")
    assert isinstance(transport, SocketNetworkTransport)

    transport.send_packet(b"session")
    assert right.recv(1024).endswith(b"session")

    adapter.close_session(session)
    with pytest.raises(RuntimeError, match="transport is closed"):
        transport.send_packet(b"after-close")
    right.close()
