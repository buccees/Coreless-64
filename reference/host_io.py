"""Concrete deterministic host I/O channel adapters for Coreless.

These adapters terminate the existing transport-neutral host contract in
memory so display, input, and network paths can be tested end-to-end without
moving computation into the host or pretending physical buses are complete.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field


@dataclass
class MemoryDisplayTransport:
    """Frame-oriented display sink/source used by the reference host boundary."""

    frames: deque[bytes] = field(default_factory=deque)

    def send_frame(self, frame: bytes) -> None:
        self.frames.append(bytes(frame))

    def receive_frame(self) -> bytes:
        if not self.frames:
            raise RuntimeError("display transport has no queued frame")
        return self.frames.popleft()


@dataclass
class MemoryInputTransport:
    """Ordered input-event transport preserving the raw event payload."""

    events: deque[bytes] = field(default_factory=deque)

    def send_event(self, event: bytes) -> None:
        self.events.append(bytes(event))

    def receive_event(self) -> bytes:
        if not self.events:
            raise RuntimeError("input transport has no queued event")
        return self.events.popleft()


@dataclass
class MemoryNetworkTransport:
    """Packet transport for deterministic host-network boundary tests."""

    packets: deque[bytes] = field(default_factory=deque)

    def send_packet(self, packet: bytes) -> None:
        self.packets.append(bytes(packet))

    def receive_packet(self) -> bytes:
        if not self.packets:
            raise RuntimeError("network transport has no queued packet")
        return self.packets.popleft()


@dataclass
class MemoryHostIO:
    """Convenience bundle for the three primary external I/O transports."""

    display: MemoryDisplayTransport = field(default_factory=MemoryDisplayTransport)
    input: MemoryInputTransport = field(default_factory=MemoryInputTransport)
    network: MemoryNetworkTransport = field(default_factory=MemoryNetworkTransport)
