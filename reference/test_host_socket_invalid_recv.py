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


def test_socket_network_transport_retires_when_packet_payload_is_truncated():
    from host_socket import SocketNetworkTransport

    class TruncatedPayloadSocket:
        closed = False

        def __init__(self):
            self.reads = [bytes.fromhex("00000005"), b"ab", b""]

        def sendall(self, data):
            raise AssertionError("sendall should not be called")

        def recv(self, size):
            chunk = self.reads.pop(0)
            assert len(chunk) <= size
            return chunk

        def close(self):
            self.closed = True

    sock = TruncatedPayloadSocket()
    transport = SocketNetworkTransport(sock)

    try:
        transport.receive_packet()
    except ConnectionError as exc:
        assert str(exc) == "host network socket closed"
    else:
        raise AssertionError("truncated packet payload was accepted")

    assert transport.closed
    assert sock.closed

def test_socket_network_transport_accepts_bytes_like_recv_chunks():
    from host_socket import SocketNetworkTransport

    class BytesLikeRecvSocket:
        closed = False

        def __init__(self):
            self.reads = [
                bytearray(bytes.fromhex("0000")),
                memoryview(bytes.fromhex("0003")),
                bytearray(b"a"),
                memoryview(b"bc"),
            ]

        def sendall(self, data):
            raise AssertionError("sendall should not be called")

        def recv(self, size):
            chunk = self.reads.pop(0)
            assert len(chunk) <= size
            return chunk

        def close(self):
            self.closed = True

    sock = BytesLikeRecvSocket()
    transport = SocketNetworkTransport(sock)

    assert transport.receive_packet() == b"abc"
    assert not transport.closed
    assert not sock.closed
    transport.close()
    assert sock.closed
