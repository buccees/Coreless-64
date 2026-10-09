def test_socket_network_transport_retires_on_invalid_recv_payload():
    from host_socket import SocketNetworkTransport

    class InvalidRecvSocket:
        closed = False

        def sendall(self, data):
            raise AssertionError("sendall should not be called")

        def recv(self, size):
            return "not-bytes"

        def close(self):
            self.closed = True

    sock = InvalidRecvSocket()
    transport = SocketNetworkTransport(sock)

    try:
        transport.receive_packet()
    except TypeError as exc:
        assert str(exc) == "host network socket recv() must return bytes"
    else:
        raise AssertionError("invalid recv payload was accepted")

    assert transport.closed
    assert sock.closed


def test_socket_network_transport_retires_when_recv_returns_more_than_requested():
    from host_socket import SocketNetworkTransport

    class OverReturningSocket:
        closed = False

        def sendall(self, data):
            raise AssertionError("sendall should not be called")

        def recv(self, size):
            assert size == 4
            return b"\x00\x00\x00\x00extra"

        def close(self):
            self.closed = True

    sock = OverReturningSocket()
    transport = SocketNetworkTransport(sock)

    try:
        transport.receive_packet()
    except ValueError as exc:
        assert str(exc) == "host network socket recv() returned more bytes than requested"
    else:
        raise AssertionError("overlong recv payload was accepted")

    assert transport.closed
    assert sock.closed
