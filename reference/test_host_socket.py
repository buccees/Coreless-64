import socket
import sys
sys.path.insert(0, ".")

import pytest

from host_socket import SocketNetworkTransport


def transport_pair():
    left, right = socket.socketpair()
    return SocketNetworkTransport(left), SocketNetworkTransport(right)


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
    sender, receiver = transport_pair()
    try:
        sender = SocketNetworkTransport(sender._socket, max_packet_size=3)
        with pytest.raises(ValueError, match="exceeds host transport limit"):
            sender.send_packet(b"1234")
    finally:
        sender.close()
        receiver.close()


def test_socket_network_transport_rejects_oversized_incoming_packet():
    sender, receiver = transport_pair()
    try:
        sender._socket.sendall(sender._HEADER.pack(4) + b"1234")
        with pytest.raises(ValueError, match="exceeds host transport limit"):
            receiver = SocketNetworkTransport(receiver._socket, max_packet_size=3)
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
    finally:
        receiver.close()
