    from host_socket import SocketNetworkTransport

    class ClosedTransport:
        closed = True

    endpoint = HostEndpoint(
        "closed-session",
        CorelessIdentity("closed-session"),
        HostCapabilities(network=True),
        {"network": ClosedTransport()},
        device_capabilities={"network"},
    )
    adapter = MemoryHostTransportAdapter([endpoint])
    interface = CorelessHostInterface(CorelessIdentity("closed-session"))
    session = adapter.open_session(endpoint, interface)

    with pytest.raises(RuntimeError, match="channels are closed"):
        session.validate()
    with pytest.raises(RuntimeError, match="channels are missing"):
        session.require_channels({"network"})


def test_socket_host_transport_session_binds_typed_network_transport():
    import socket