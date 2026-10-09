"""Socket-backed host network transport for the Coreless host boundary.

This adapter carries Coreless network packets over an already-connected host
socket. The host owns the socket; Coreless remains the computational owner.
Packets use a deterministic 32-bit big-endian length prefix so arbitrary packet
bytes can cross a stream transport without ambiguity.
"""

from __future__ import annotations

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
        if not all(callable(getattr(sock, name, None)) for name in ("sendall", "recv", "close")):
            raise TypeError("sock must provide sendall(), recv(), and close()")
        if isinstance(max_packet_size, bool) or not isinstance(max_packet_size, int):
            raise TypeError("max_packet_size must be an integer")
        if max_packet_size <= 0:
            raise ValueError("max_packet_size must be positive")
        if max_packet_size > self._MAX_PACKET:
            raise ValueError("max_packet_size exceeds Coreless host limit")
        closed = bool(getattr(sock, "closed", False))
        if not closed:
            fileno = getattr(sock, "fileno", None)
            if callable(fileno):
                try:
                    closed = fileno() < 0
                except (OSError, ValueError):
                    closed = True
        if closed:
            raise RuntimeError("host network socket is already closed")
        self._socket = sock
        self._max_packet_size = max_packet_size
        self._closed = False

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def socket(self) -> SocketLike:
        """Return the host-owned socket for adapter lifecycle comparison."""
        return self._socket

    def send_packet(self, packet: bytes) -> None:
        """Send one length-delimited packet."""
        self._ensure_open()
        # Validate caller input before touching the stream. Local argument
        # errors must not retire an otherwise healthy connection.
        if not isinstance(packet, (bytes, bytearray, memoryview)):
            raise TypeError("network packet must be bytes-like")
        payload = bytes(packet)
        if len(payload) > self._max_packet_size:
            raise ValueError("network packet exceeds host transport limit")
        try:
            self._socket.sendall(self._HEADER.pack(len(payload)) + payload)
        except (ConnectionError, OSError, TypeError, ValueError):
            self._retire_after_transport_error()
            raise

    def receive_packet(self) -> bytes:
        """Receive exactly one length-delimited packet."""
        self._ensure_open()
        try:
            header = self._recv_exact(self._HEADER.size)
            (size,) = self._HEADER.unpack(header)
            if size > self._max_packet_size:
                self._close_after_protocol_error()
                raise ValueError("network packet exceeds host transport limit")
            return self._recv_exact(size)
        except (ConnectionError, OSError, TypeError, ValueError):
            self._retire_after_transport_error()
            raise

    def close(self) -> None:
        """Close the host-owned socket without changing Coreless state."""
        if not self._closed:
            try:
                self._socket.close()
            finally:
                self._closed = True

    def __enter__(self) -> "SocketNetworkTransport":
        """Return the live transport for scoped host socket ownership."""
        self._ensure_open()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """Retire the transport when its scoped ownership ends."""
        if exc_type is None:
            self.close()
            return
        try:
            self.close()
        except Exception:
            # Cleanup must not mask the exception raised by the scoped body.
            pass

    def retire_without_closing_socket(self) -> None:
        """Invalidate this wrapper while leaving a shared socket usable."""
        self._closed = True

    def _recv_exact(self, size: int) -> bytes:
        chunks = bytearray()
        while len(chunks) < size:
            chunk = self._socket.recv(size - len(chunks))
            if not chunk:
                raise ConnectionError("host network socket closed")
            if not isinstance(chunk, (bytes, bytearray, memoryview)):
                self._retire_socket()
                raise TypeError("host network socket recv() must return bytes")
            chunks.extend(chunk)
        return bytes(chunks)

    def _close_after_protocol_error(self) -> None:
        """Retire the stream after an invalid frame length is observed."""
        self._retire_socket()

    def _retire_after_transport_error(self) -> None:
        """Mark a failed stream closed and best-effort close the host socket."""
        self._retire_socket()

    def _retire_socket(self) -> None:
        self._closed = True
        try:
            self._socket.close()
        except Exception:
            # Retirement cleanup is best-effort and must not mask the
            # transport failure that triggered it.
            pass

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("host network transport is closed")
