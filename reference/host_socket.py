"""Socket-backed host network transport for the Coreless host boundary.

This adapter carries Coreless network packets over an already-connected host
socket. The host owns the socket; Coreless remains the computational owner.
Packets use a deterministic 32-bit big-endian length prefix so arbitrary packet
bytes can cross a stream transport without ambiguity.
"""

from __future__ import annotations

import socket
import struct
from typing import Protocol


class SocketLike(Protocol):
    def sendall(self, data: bytes) -> None:
        ...

    def recv(self, size: int) -> bytes:
        ...

    def close(self) -> None:
        ...


class SocketNetworkTransport:
    """NetworkTransport implementation over a connected stream socket."""

    _HEADER = struct.Struct(">I")
    _MAX_PACKET = 16 * 1024 * 1024

    def __init__(self, sock: SocketLike, *, max_packet_size: int = _MAX_PACKET) -> None:
        if max_packet_size <= 0:
            raise ValueError("max_packet_size must be positive")
        if max_packet_size > self._MAX_PACKET:
            raise ValueError("max_packet_size exceeds Coreless host limit")
        self._socket = sock
        self._max_packet_size = max_packet_size
        self._closed = False

    @property
    def closed(self) -> bool:
        return self._closed

    def send_packet(self, packet: bytes) -> None:
        """Send one length-delimited packet."""
        self._ensure_open()
        payload = bytes(packet)
        if len(payload) > self._max_packet_size:
            raise ValueError("network packet exceeds host transport limit")
        self._socket.sendall(self._HEADER.pack(len(payload)) + payload)

    def receive_packet(self) -> bytes:
        """Receive exactly one length-delimited packet."""
        self._ensure_open()
        header = self._recv_exact(self._HEADER.size)
        (size,) = self._HEADER.unpack(header)
        if size > self._max_packet_size:
            raise ValueError("network packet exceeds host transport limit")
        return self._recv_exact(size)

    def close(self) -> None:
        """Close the host-owned socket without changing Coreless state."""
        if not self._closed:
            self._socket.close()
            self._closed = True

    def _recv_exact(self, size: int) -> bytes:
        chunks = bytearray()
        while len(chunks) < size:
            chunk = self._socket.recv(size - len(chunks))
            if not chunk:
                raise ConnectionError("host network socket closed")
            chunks.extend(chunk)
        return bytes(chunks)

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("host network transport is closed")
