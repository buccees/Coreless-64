import socket
import sys
sys.path.insert(0, ".")

import pytest

from host_io import NetworkTransport
from host_socket import SocketNetworkTransport


def transport_pair():
    left, right = socket.socketpair()
    return SocketNetworkTransport(left), SocketNetworkTransport(right)


def test_socket_network_transport_implements_network_contract():
    left, right = socket.socketpair()
    transport = SocketNetworkTransport(left)
    try:
        assert isinstance(transport, NetworkTransport)
    finally:
        transport.close()
        right.close()


def test_socket_network_transport_round_trip():
    sender, receiver = transport_pair()
    try:
        sender.send_packet(b"coreless-network-packet")
        assert receiver.receive_packet() == b"coreless-network-packet"
    finally:
        sender.close()
        receiver.close()


def test_socket_network_transport_handles_empty_packet():
    sender, receiver = transport_pair()
    try:
        sender.send_packet(b"")
        assert receiver.receive_packet() == b""
    finally:
        sender.close()
        receiver.close()


def test_socket_network_transport_rejects_oversized_packet_without_retiring_stream():
    sender, receiver = transport_pair()
    sender._max_packet_size = 3
    try:
        with pytest.raises(ValueError, match="exceeds host transport limit"):
            sender.send_packet(b"1234")
        assert not sender.closed
        sender.send_packet(b"ok")
        assert receiver.receive_packet() == b"ok"
    finally:
        sender.close()
        receiver.close()


def test_socket_network_transport_rejects_non_bytes_packet_without_retiring_stream():
    sender, receiver = transport_pair()
    try:
        with pytest.raises(TypeError, match="must be bytes-like"):
            sender.send_packet(4)
        assert not sender.closed
        sender.send_packet(b"ok")
        assert receiver.receive_packet() == b"ok"
    finally:
        sender.close()
        receiver.close()


def test_socket_network_transport_rejects_oversized_incoming_packet():
    left, right = socket.socketpair()
    sender = SocketNetworkTransport(left)
    receiver = SocketNetworkTransport(right, max_packet_size=3)
    try:
        sender.send_packet(b"1234")
        with pytest.raises(ValueError, match="exceeds host transport limit"):
            receiver.receive_packet()
        assert receiver.closed
        with pytest.raises(RuntimeError, match="transport is closed"):
            receiver.receive_packet()
    finally:
        sender.close()
        receiver.close()


def test_socket_network_transport_retires_on_oversized_incoming_header():
    left, right = socket.socketpair()
    receiver = SocketNetworkTransport(right, max_packet_size=3)
    try:
        left.sendall((4).to_bytes(4, "big"))
        with pytest.raises(ValueError, match="exceeds host transport limit"):
            receiver.receive_packet()
        assert receiver.closed
    finally:
        receiver.close()
        left.close()



def test_socket_network_transport_rejects_already_closed_raw_socket():
    left, right = socket.socketpair()
    left.close()
    try:
        with pytest.raises(RuntimeError, match="socket is already closed"):
            SocketNetworkTransport(left)
    finally:
        right.close()


def test_socket_network_transport_accepts_socket_like_closed_contract():
    class SocketLikeClosed:
        closed = False

        def sendall(self, data):
            raise AssertionError("sendall should not be called")

        def recv(self, size):
            raise AssertionError("recv should not be called")

        def close(self):
            pass

    transport = SocketNetworkTransport(SocketLikeClosed())
    assert not transport.closed
    transport.close()


def test_socket_network_transport_preserves_transport_error_when_close_fails():
    class FailingCloseSocket:
        def sendall(self, data):
            raise OSError("send failed")

        def recv(self, size):
            raise AssertionError("recv should not be called")

        def close(self):
            raise ValueError("close failed")

    transport = SocketNetworkTransport(FailingCloseSocket())

    with pytest.raises(OSError, match="send failed"):
        transport.send_packet(b"x")
    assert transport.closed



def test_socket_network_transport_receive_failure_survives_close_error():
    class FailingCloseSocket:
        def recv(self, size):
            raise OSError("recv failed")

        def sendall(self, data):
            raise AssertionError("sendall should not be called")

        def close(self):
            raise ValueError("close failed")

    transport = SocketNetworkTransport(FailingCloseSocket())

    with pytest.raises(OSError, match="recv failed"):
        transport.receive_packet()
    assert transport.closed



def test_socket_network_transport_rejects_use_after_close():
    sender, receiver = transport_pair()
    sender.close()
    try:
        with pytest.raises(RuntimeError, match="transport is closed"):
            sender.send_packet(b"x")
    finally:
        receiver.close()


def test_socket_network_transport_detects_peer_close():
    sender, receiver = transport_pair()
    sender.close()
    try:
        with pytest.raises(ConnectionError, match="socket closed"):
            receiver.receive_packet()
        assert receiver.closed
    finally:
        receiver.close()


def test_socket_network_transport_marks_send_failure_closed():
    left, right = socket.socketpair()
    transport = SocketNetworkTransport(left)
    left.close()
    try:
        with pytest.raises(OSError):
            transport.send_packet(b"send-failure")
        assert transport.closed
        with pytest.raises(RuntimeError, match="transport is closed"):
            transport.send_packet(b"after-failure")
    finally:
        right.close()


def test_socket_network_transport_marks_partial_receive_failure_closed():
    left, right = socket.socketpair()
    receiver = SocketNetworkTransport(right)
    try:
        left.sendall((5).to_bytes(4, "big") + b"x")
        left.close()
        with pytest.raises(ConnectionError, match="socket closed"):
            receiver.receive_packet()
        assert receiver.closed
    finally:
        receiver.close()


def test_socket_network_transport_rejects_invalid_packet_size():
    left, right = socket.socketpair()
    try:
        with pytest.raises(ValueError, match="must be positive"):
            SocketNetworkTransport(left, max_packet_size=0)
        with pytest.raises(ValueError, match="exceeds Coreless host limit"):
            SocketNetworkTransport(left, max_packet_size=17 * 1024 * 1024)
    finally:
        left.close()
        right.close()


def test_socket_network_transport_close_is_idempotent():
    class CountingSocket:
        def __init__(self):
            self.close_calls = 0

        def sendall(self, data):
            raise AssertionError("sendall should not be called")

        def recv(self, size):
            raise AssertionError("recv should not be called")

        def close(self):
            self.close_calls += 1

    sock = CountingSocket()
    transport = SocketNetworkTransport(sock)

    transport.close()
    transport.close()

    assert transport.closed
    assert sock.close_calls == 1


def test_socket_network_transport_context_manager_closes_on_body_failure():
    class CountingSocket:
        def __init__(self):
            self.close_calls = 0

        def sendall(self, data):
            raise AssertionError("sendall should not be called")

        def recv(self, size):
            raise AssertionError("recv should not be called")

        def close(self):
            self.close_calls += 1

    sock = CountingSocket()

    with pytest.raises(RuntimeError, match="body failed"):
        with SocketNetworkTransport(sock) as transport:
            assert not transport.closed
            raise RuntimeError("body failed")

    assert transport.closed
    assert sock.close_calls == 1


def test_socket_network_transport_context_manager_closes_once():
    class CountingSocket:
        def __init__(self):
            self.close_calls = 0

        def sendall(self, data):
            raise AssertionError("sendall should not be called")

        def recv(self, size):
            raise AssertionError("recv should not be called")

        def close(self):
            self.close_calls += 1

    sock = CountingSocket()
    with SocketNetworkTransport(sock) as transport:
        assert not transport.closed
    assert transport.closed
    assert sock.close_calls == 1


def test_socket_network_transport_context_manager_preserves_body_error_when_close_fails():
    class FailingCloseSocket:
        def sendall(self, data):
            raise AssertionError("sendall should not be called")

        def recv(self, size):
            raise AssertionError("recv should not be called")

        def close(self):
            raise ValueError("close failed")

    with pytest.raises(RuntimeError, match="body failed"):
        with SocketNetworkTransport(FailingCloseSocket()) as transport:
            assert not transport.closed
            raise RuntimeError("body failed")

    assert transport.closed


def test_socket_network_transport_marks_send_value_error_closed():
    class ValueErrorSocket:
        def sendall(self, data):
            raise ValueError("send value failed")

        def recv(self, size):
            raise AssertionError("recv should not be called")

        def close(self):
            pass

    transport = SocketNetworkTransport(ValueErrorSocket())

    with pytest.raises(ValueError, match="send value failed"):
        transport.send_packet(b"x")

    assert transport.closed
    with pytest.raises(RuntimeError, match="transport is closed"):
        transport.send_packet(b"again")


def test_socket_network_transport_marks_receive_value_error_closed():
    class ValueErrorSocket:
        def recv(self, size):
            raise ValueError("recv value failed")

        def sendall(self, data):
            raise AssertionError("sendall should not be called")

        def close(self):
            pass

    transport = SocketNetworkTransport(ValueErrorSocket())

    with pytest.raises(ValueError, match="recv value failed"):
        transport.receive_packet()

    assert transport.closed
    with pytest.raises(RuntimeError, match="transport is closed"):
        transport.receive_packet()


def test_socket_network_transport_retirement_ignores_unexpected_close_error():
    class RuntimeErrorSocket:
        def sendall(self, data):
            raise ConnectionError("send failed")

        def recv(self, size):
            raise AssertionError("recv should not be called")

        def close(self):
            raise RuntimeError("cleanup failed")

    transport = SocketNetworkTransport(RuntimeErrorSocket())

    with pytest.raises(ConnectionError, match="send failed"):
        transport.send_packet(b"x")

    assert transport.closed
    with pytest.raises(RuntimeError, match="transport is closed"):
        transport.send_packet(b"again")


def test_socket_network_transport_marks_send_type_error_closed():
    class TypeErrorSocket:
        def sendall(self, data):
            raise TypeError("send type failed")

        def recv(self, size):
            raise AssertionError("recv should not be called")

        def close(self):
            pass

    transport = SocketNetworkTransport(TypeErrorSocket())

    with pytest.raises(TypeError, match="send type failed"):
        transport.send_packet(b"x")

    assert transport.closed
    with pytest.raises(RuntimeError, match="transport is closed"):
        transport.send_packet(b"again")


def test_socket_network_transport_marks_receive_type_error_closed():
    class TypeErrorSocket:
        def recv(self, size):
            raise TypeError("recv type failed")

        def sendall(self, data):
            raise AssertionError("sendall should not be called")

        def close(self):
            pass

    transport = SocketNetworkTransport(TypeErrorSocket())

    with pytest.raises(TypeError, match="recv type failed"):
        transport.receive_packet()

    assert transport.closed
    with pytest.raises(RuntimeError, match="transport is closed"):
        transport.receive_packet()


def test_socket_network_transport_rejects_arbitrary_packet_conversion():
    class ConversionErrorPacket:
        def __bytes__(self):
            raise AssertionError("arbitrary conversion must not be invoked")

    class TrackingSocket:
        def sendall(self, data):
            raise AssertionError("sendall should not be called")

        def recv(self, size):
            raise AssertionError("recv should not be called")

        def close(self):
            pass

    transport = SocketNetworkTransport(TrackingSocket())

    with pytest.raises(TypeError, match="must be bytes-like"):
        transport.send_packet(ConversionErrorPacket())

    assert not transport.closed
    transport.close()



def test_socket_network_transport_serializes_concurrent_packet_sends():
    from concurrent.futures import ThreadPoolExecutor

    sender, receiver = transport_pair()
    packets = [f"packet-{worker}-{index}".encode() for worker in range(8) for index in range(40)]
    try:
        # Drain concurrently: a stream socket's send buffer is finite, so
        # sending every frame before reading can deadlock independently of
        # frame serialization.
        with ThreadPoolExecutor(max_workers=9) as pool:
            receive_future = pool.submit(lambda: [receiver.receive_packet() for _ in packets])
            list(pool.map(sender.send_packet, packets))
            received = receive_future.result(timeout=10)
        assert sorted(received) == sorted(packets)
    finally:
        sender.close()
        receiver.close()


def test_socket_network_transport_serializes_concurrent_packet_receives():
    from concurrent.futures import ThreadPoolExecutor

    sender, receiver = transport_pair()
    packets = [f"receive-{worker}-{index}".encode() for worker in range(6) for index in range(30)]
    try:
        for packet in packets:
            sender.send_packet(packet)
        with ThreadPoolExecutor(max_workers=6) as pool:
            received_groups = list(pool.map(lambda _: [receiver.receive_packet() for _ in range(30)], range(6)))
        received = [packet for group in received_groups for packet in group]
        assert sorted(received) == sorted(packets)
    finally:
        sender.close()
        receiver.close()


def test_socket_network_transport_concurrent_close_is_idempotent():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Lock

    class CountingSocket:
        def __init__(self):
            self.close_calls = 0
            self.lock = Lock()

        def sendall(self, data):
            raise AssertionError("sendall should not be called")

        def recv(self, size):
            raise AssertionError("recv should not be called")

        def close(self):
            with self.lock:
                self.close_calls += 1

    sock = CountingSocket()
    transport = SocketNetworkTransport(sock)
    with ThreadPoolExecutor(max_workers=16) as pool:
        list(pool.map(lambda _: transport.close(), range(128)))

    assert transport.closed
    assert sock.close_calls == 1


def test_socket_network_transport_close_interrupts_blocked_receive():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    left, right = socket.socketpair()
    receive_started = Event()

    class SignalingSocket:
        def sendall(self, data):
            right.sendall(data)

        def recv(self, size):
            receive_started.set()
            return right.recv(size)

        def shutdown(self, how):
            right.shutdown(how)

        def close(self):
            right.close()

    receiver = SocketNetworkTransport(SignalingSocket())
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(receiver.receive_packet)
            assert receive_started.wait(timeout=2)
            receiver.close()
            with pytest.raises(ConnectionError, match="socket closed"):
                future.result(timeout=2)
    finally:
        receiver.close()
        left.close()


def test_socket_network_transport_error_retirement_interrupts_blocked_receive():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    left, right = socket.socketpair()
    receive_started = Event()

    class SignalingSocket:
        def sendall(self, data):
            right.sendall(data)

        def recv(self, size):
            receive_started.set()
            return right.recv(size)

        def shutdown(self, how):
            right.shutdown(how)

        def close(self):
            right.close()

    receiver = SocketNetworkTransport(SignalingSocket())
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(receiver.receive_packet)
            assert receive_started.wait(timeout=2)
            # Simulate a concurrent I/O path retiring a now-unusable stream.
            receiver._retire_after_transport_error()
            with pytest.raises(ConnectionError, match="socket closed"):
                future.result(timeout=2)
        assert receiver.closed
    finally:
        receiver.close()
        left.close()


def test_socket_network_transport_close_interrupts_blocked_send():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    left, right = socket.socketpair()
    left.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4096)
    send_started = Event()

    class SignalingSocket:
        def sendall(self, data):
            send_started.set()
            left.sendall(data)

        def recv(self, size):
            return left.recv(size)

        def shutdown(self, how):
            left.shutdown(how)

        def close(self):
            left.close()

    sender = SocketNetworkTransport(SignalingSocket())
    # Do not read from the peer: the large frame must block in sendall.
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(sender.send_packet, b"x" * (8 * 1024 * 1024))
            assert send_started.wait(timeout=2)
            sender.close()
            with pytest.raises(OSError):
                future.result(timeout=2)
        assert sender.closed
    finally:
        sender.close()
        right.close()


def test_socket_network_transport_close_still_closes_when_shutdown_fails():
    class ShutdownFailingSocket:
        def __init__(self):
            self.shutdown_calls = 0
            self.close_calls = 0

        def sendall(self, data):
            raise AssertionError("sendall should not be called")

        def recv(self, size):
            raise AssertionError("recv should not be called")

        def shutdown(self, how):
            self.shutdown_calls += 1
            raise OSError("already disconnected")

        def close(self):
            self.close_calls += 1

    sock = ShutdownFailingSocket()
    transport = SocketNetworkTransport(sock)

    transport.close()
    transport.close()

    assert transport.closed
    assert sock.shutdown_calls == 1
    assert sock.close_calls == 1


def test_socket_network_transport_retires_if_recv_exceeds_requested_size():
    class OverreadingSocket:
        def sendall(self, data):
            raise AssertionError("sendall should not be called")

        def recv(self, size):
            return b"x" * (size + 1)

        def close(self):
            self.closed = True

    sock = OverreadingSocket()
    transport = SocketNetworkTransport(sock)

    with pytest.raises(ValueError, match="more bytes than requested"):
        transport.receive_packet()

    assert transport.closed
    with pytest.raises(RuntimeError, match="transport is closed"):
        transport.receive_packet()
