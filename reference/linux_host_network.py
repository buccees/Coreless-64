"""Linux TCP bootstrap provider for configured Coreless host endpoints.

This is a concrete, configured-network adapter, not automatic enumeration of
arbitrary physical buses. A peer must implement the documented discovery
exchange: receive CORELESS_DISCOVERY_REQUEST as one framed packet and return
one encoded DeviceIdentityFrame as one framed packet on the same connection.
The established socket remains the negotiated network channel.
"""
from __future__ import annotations

import math
import socket
import ssl
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
    expected_computer_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.host, str) or not self.host.strip():
            raise ValueError("Linux TCP endpoint host must not be empty")
        if isinstance(self.port, bool) or not isinstance(self.port, int):
            raise TypeError("Linux TCP endpoint port must be an integer")
        if not 1 <= self.port <= 65535:
            raise ValueError("Linux TCP endpoint port must be between 1 and 65535")
        if not isinstance(self.expected_computer_id, str) or not self.expected_computer_id.strip():
            raise ValueError("expected Coreless computer identity must not be empty")


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
        ssl_context: ssl.SSLContext,
        timeout: float = 3.0,
        max_packet_size: int = 16 * 1024 * 1024,
    ) -> None:
        if sys.platform != "linux":
            raise RuntimeError("LinuxTCPDiscoveryProvider requires Linux")
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
            raise TypeError("timeout must be a positive number")
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be positive and finite")
        self._endpoints = tuple(endpoints)
        if any(not isinstance(endpoint, LinuxTCPEndpoint) for endpoint in self._endpoints):
            raise TypeError("endpoints must contain LinuxTCPEndpoint values")
        ids = [self._endpoint_id(endpoint) for endpoint in self._endpoints]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate configured Linux TCP endpoint")
        if not all(hasattr(ssl_context, name) for name in ("verify_mode", "check_hostname", "wrap_socket")):
            raise TypeError("ssl_context must provide verified TLS context settings and wrap_socket()")
        if ssl_context.verify_mode != ssl.CERT_REQUIRED or not ssl_context.check_hostname:
            raise ValueError("TLS context must require certificate validation and hostname checking")
        if isinstance(max_packet_size, bool) or not isinstance(max_packet_size, int):
            raise TypeError("max_packet_size must be an integer")
        if max_packet_size <= 0:
            raise ValueError("max_packet_size must be positive")
        if max_packet_size > SocketNetworkTransport._MAX_PACKET:
            raise ValueError("max_packet_size exceeds Coreless host limit")
        self._ssl_context = ssl_context
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
            transport = None
            tls_socket = None
            try:
                # Keep every post-connect setup operation inside the cleanup
                # boundary so a timeout-configuration failure cannot leak the
                # newly opened host socket.
                raw_socket.settimeout(self._timeout)
                tls_socket = self._ssl_context.wrap_socket(
                    raw_socket, server_hostname=endpoint.host
                )
                tls_socket.settimeout(self._timeout)
                transport = SocketNetworkTransport(
                    tls_socket, max_packet_size=self._max_packet_size
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
                if computer_id != endpoint.expected_computer_id:
                    raise ValueError("Coreless identity does not match configured endpoint")
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
                elif tls_socket is not None:
                    # wrap_socket() may transfer ownership away from the raw
                    # socket. If TLS setup fails before transport construction,
                    # close the wrapped socket rather than the detached raw one.
                    try:
                        tls_socket.close()
                    except Exception:
                        pass
                else:
                    try:
                        raw_socket.close()
                    except Exception:
                        pass
                raise
        return tuple(candidates)
