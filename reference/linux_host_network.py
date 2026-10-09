"""Linux TCP bootstrap provider for configured Coreless host endpoints.

This is a concrete, configured-network adapter, not automatic enumeration of
arbitrary physical buses. A peer must implement the documented discovery
exchange: receive CORELESS_DISCOVERY_REQUEST as one framed packet and return
one encoded DeviceIdentityFrame as one framed packet on the same connection.
The established socket remains the negotiated network channel.
"""
from __future__ import annotations

import socket
import sys
from dataclasses import dataclass
from typing import Iterable

from device_protocol import DeviceIdentityFrame
from host_discovery import HostDiscoveryCandidate
from host_interface import HostCapabilities
from host_socket import SocketNetworkTransport


DISCOVERY_REQUEST = b"CORELESS_DISCOVERY_V1"


@dataclass(frozen=True)
class LinuxTCPEndpoint:
    """Explicitly configured TCP endpoint for a Coreless peer."""

    host: str
    port: int

    def __post_init__(self) -> None:
        if not isinstance(self.host, str) or not self.host.strip():
            raise ValueError("Linux TCP endpoint host must not be empty")
        if isinstance(self.port, bool) or not isinstance(self.port, int):
            raise TypeError("Linux TCP endpoint port must be an integer")
        if not 1 <= self.port <= 65535:
            raise ValueError("Linux TCP endpoint port must be between 1 and 65535")


class LinuxTCPDiscoveryProvider:
    """Discover configured Coreless peers over a framed TCP bootstrap.

    The provider never scans the network or infers device identity from DNS,
    an IP address, or a port. The endpoint must return a valid Coreless identity
    frame. Failed endpoints fail the discovery call rather than being silently
    reported as available.
    """

    def __init__(
        self,
        endpoints: Iterable[LinuxTCPEndpoint],
        *,
        timeout: float = 3.0,
        max_packet_size: int = 16 * 1024 * 1024,
    ) -> None:
        if sys.platform != "linux":
            raise RuntimeError("LinuxTCPDiscoveryProvider requires Linux")
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
            raise TypeError("timeout must be a positive number")
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self._endpoints = tuple(endpoints)
        if any(not isinstance(endpoint, LinuxTCPEndpoint) for endpoint in self._endpoints):
            raise TypeError("endpoints must contain LinuxTCPEndpoint values")
        ids = [self._endpoint_id(endpoint) for endpoint in self._endpoints]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate configured Linux TCP endpoint")
        self._timeout = float(timeout)
        self._max_packet_size = max_packet_size

    @staticmethod
    def _endpoint_id(endpoint: LinuxTCPEndpoint) -> str:
        return f"tcp://{endpoint.host}:{endpoint.port}"

    def enumerate_candidates(self) -> tuple[HostDiscoveryCandidate, ...]:
        """Connect to each configured peer and validate its identity response."""
        candidates = []
        for endpoint in self._endpoints:
            raw_socket = socket.create_connection(
                (endpoint.host, endpoint.port), timeout=self._timeout
            )
            raw_socket.settimeout(self._timeout)
            transport = None
            try:
                transport = SocketNetworkTransport(
                    raw_socket, max_packet_size=self._max_packet_size
                )
                transport.send_packet(DISCOVERY_REQUEST)
                identity_payload = transport.receive_packet()
                identity = DeviceIdentityFrame.decode(identity_payload)
                if identity.protocol_version <= 0:
                    raise ValueError("invalid Coreless discovery protocol version")
                # Requiring a nonempty UTF-8 identity here prevents a connection
                # from being surfaced as a candidate before neutral validation.
                computer_id = identity.payload.decode("utf-8")
                if not computer_id:
                    raise ValueError("Coreless discovery identity is empty")
                candidates.append(
                    HostDiscoveryCandidate(
                        endpoint_id=self._endpoint_id(endpoint),
                        identity_frame=identity,
                        host_capabilities=HostCapabilities(network=True),
                        channels={"network": transport},
                    )
                )
            except Exception:
                if transport is not None:
                    try:
                        transport.close()
                    except Exception:
                        pass
                else:
                    try:
                        raw_socket.close()
                    except Exception:
                        pass
                raise
        return tuple(candidates)
