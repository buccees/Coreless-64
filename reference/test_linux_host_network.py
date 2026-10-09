import socket
import sys
import threading

sys.path.insert(0, ".")
import pytest

from device_protocol import (
    ARCHITECTURE_CORELESS64,
    DEVICE_TYPE_CORELESS64,
    DeviceIdentityFrame,
    capability_bits,
)
from host_discovery import HostDeviceEnumerator
from host_socket import SocketNetworkTransport
from linux_host_network import (
    DISCOVERY_REQUEST,
    LinuxTCPDiscoveryProvider,
    LinuxTCPEndpoint,
)


def identity_frame(computer_id="coreless-linux", capabilities=("network",)):
    return DeviceIdentityFrame(
        protocol_version=1,
        architecture=ARCHITECTURE_CORELESS64,
        device_type=DEVICE_TYPE_CORELESS64,
        capabilities=capability_bits(set(capabilities)),
        payload=computer_id.encode("utf-8"),
    ).encode()


def start_peer(reply):
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]
    seen = []
    errors = []

    def serve():
        try:
            conn, _ = listener.accept()
            with conn:
                transport = SocketNetworkTransport(conn)
                try:
                    seen.append(transport.receive_packet())
                    transport.send_packet(reply)
                    # Keep the connection alive until the test closes its channel.
                    try:
                        seen.append(transport.receive_packet())
                    except (ConnectionError, OSError, RuntimeError):
                        pass
                finally:
                    transport.retire_without_closing_socket()
        except Exception as exc:
            errors.append(exc)
        finally:
            listener.close()

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    return port, seen, errors, thread


def test_linux_tcp_provider_exchanges_identity_and_retains_network_channel():
    port, seen, errors, thread = start_peer(identity_frame())
    provider = LinuxTCPDiscoveryProvider(
        [LinuxTCPEndpoint("127.0.0.1", port)], timeout=1
    )
    candidates = provider.enumerate_candidates()
    endpoints = HostDeviceEnumerator().discover(candidates)
    assert seen == [DISCOVERY_REQUEST]
    assert endpoints[0].identity.computer_id == "coreless-linux"
    assert endpoints[0].device_capabilities == frozenset({"network"})
    channel = endpoints[0].channel_map()["network"]
    assert isinstance(channel, SocketNetworkTransport)
    channel.send_packet(b"post-discovery")
    channel.close()
    thread.join(timeout=1)
    assert not thread.is_alive()
    assert not errors
    assert seen == [DISCOVERY_REQUEST, b"post-discovery"]


def test_linux_tcp_provider_rejects_invalid_identity_and_closes_channel():
    port, seen, errors, thread = start_peer(b"not-an-identity-frame")
    provider = LinuxTCPDiscoveryProvider(
        [LinuxTCPEndpoint("127.0.0.1", port)], timeout=1
    )
    with pytest.raises(ValueError):
        provider.enumerate_candidates()
    thread.join(timeout=1)
    assert not thread.is_alive()
    assert not errors


def test_linux_tcp_provider_rejects_duplicate_configured_endpoints():
    endpoint = LinuxTCPEndpoint("127.0.0.1", 12345)
    with pytest.raises(ValueError, match="duplicate configured"):
        LinuxTCPDiscoveryProvider([endpoint, endpoint])


@pytest.mark.parametrize("host,port,error", [
    ("", 1234, ValueError),
    ("127.0.0.1", 0, ValueError),
    ("127.0.0.1", 65536, ValueError),
    ("127.0.0.1", True, TypeError),
])
def test_linux_tcp_endpoint_validates_configuration(host, port, error):
    with pytest.raises(error):
        LinuxTCPEndpoint(host, port)


def test_linux_tcp_provider_requires_positive_timeout():
    with pytest.raises(ValueError, match="timeout must be positive"):
        LinuxTCPDiscoveryProvider([], timeout=0)
