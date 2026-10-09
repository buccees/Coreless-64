import socket
import ssl
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


class TestTLSContext:
    """Test-only TLS shim; not a security or TLS interoperability test."""
    verify_mode = ssl.CERT_REQUIRED
    check_hostname = True

    def wrap_socket(self, sock, *, server_hostname):
        self.server_hostname = server_hostname
        return sock


def make_test_tls_context():
    return TestTLSContext()


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
    # Use a verified context. Loopback peer tests exercise protocol framing;
    # TLS handshake behavior is covered by the provider's required context policy.
    provider = LinuxTCPDiscoveryProvider(
        [LinuxTCPEndpoint("localhost", port, "coreless-linux")],
        ssl_context=make_test_tls_context(), timeout=1
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
        [LinuxTCPEndpoint("127.0.0.1", port, "coreless-linux")], ssl_context=make_test_tls_context(), timeout=1
    )
    with pytest.raises(ValueError):
        provider.enumerate_candidates()
    thread.join(timeout=1)
    assert not thread.is_alive()
    assert not errors


def test_linux_tcp_provider_rejects_duplicate_configured_endpoints():
    endpoint = LinuxTCPEndpoint("127.0.0.1", 12345, "coreless-linux")
    with pytest.raises(ValueError, match="duplicate configured"):
        LinuxTCPDiscoveryProvider([endpoint, endpoint], ssl_context=make_test_tls_context())


@pytest.mark.parametrize("host,port,error", [
    ("", 1234, ValueError),
    ("127.0.0.1", 0, ValueError),
    ("127.0.0.1", 65536, ValueError),
    ("127.0.0.1", True, TypeError),
])
def test_linux_tcp_endpoint_validates_configuration(host, port, error):
    with pytest.raises(error):
        LinuxTCPEndpoint(host, port, "coreless-linux")


def test_linux_tcp_provider_requires_positive_timeout():
    with pytest.raises(ValueError, match="timeout must be positive"):
        LinuxTCPDiscoveryProvider([], ssl_context=make_test_tls_context(), timeout=0)


@pytest.mark.parametrize("max_packet_size,error,match", [
    (0, ValueError, "max_packet_size must be positive"),
    (-1, ValueError, "max_packet_size must be positive"),
    (True, TypeError, "max_packet_size must be an integer"),
    (1.5, TypeError, "max_packet_size must be an integer"),
    (16 * 1024 * 1024 + 1, ValueError, "exceeds Coreless host limit"),
])
def test_linux_tcp_provider_rejects_invalid_packet_limit(max_packet_size, error, match):
    with pytest.raises(error, match=match):
        LinuxTCPDiscoveryProvider(
            [], ssl_context=make_test_tls_context(), max_packet_size=max_packet_size
        )



def test_linux_tcp_provider_rejects_unverified_tls_context():
    class UnverifiedContext:
        verify_mode = ssl.CERT_NONE
        check_hostname = False
        def wrap_socket(self, sock, *, server_hostname):
            return sock

    with pytest.raises(ValueError, match="require certificate validation"):
        LinuxTCPDiscoveryProvider([], ssl_context=UnverifiedContext())


def test_linux_tcp_provider_requires_tls_context():
    with pytest.raises(TypeError, match="ssl_context"):
        LinuxTCPDiscoveryProvider([])

def test_linux_tcp_provider_closes_socket_if_timeout_setup_fails(monkeypatch):
    class TimeoutFailSocket:
        closed = False

        def settimeout(self, timeout):
            raise OSError("timeout setup failed")

        def close(self):
            self.closed = True

    sock = TimeoutFailSocket()
    monkeypatch.setattr("linux_host_network.socket.create_connection", lambda *a, **k: sock)
    provider = LinuxTCPDiscoveryProvider(
        [LinuxTCPEndpoint("localhost", 12345, "coreless-linux")],
        ssl_context=make_test_tls_context(),
    )
    with pytest.raises(OSError, match="timeout setup failed"):
        provider.enumerate_candidates()
    assert sock.closed
