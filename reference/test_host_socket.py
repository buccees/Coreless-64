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


def test_socket_network_transport_rejects_oversized_packet():
    left, right = socket.socketpair()
    sender = SocketNetworkTransport(left, max_packet_size=3)
    receiver = SocketNetworkTransport(right)
    try:
        with pytest.raises(ValueError, match="exceeds host transport limit"):
            sender.send_packet(b"1234")
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
    finally:
        sender.close()
        receiver.close()


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
