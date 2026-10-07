"""Platform-independent Coreless host endpoint discovery.

This layer turns transport-neutral identity advertisements into validated
HostEndpoint objects. Physical USB/PCIe/network enumeration remains outside
this module.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Protocol

from device_protocol import DeviceIdentityFrame
from host_interface import CorelessIdentity, HostCapabilities
from host_transport import HostEndpoint


@dataclass(frozen=True)
class HostDiscoveryCandidate:
    """Raw discovery result supplied by any concrete host transport."""

    endpoint_id: str
    identity_frame: bytes | DeviceIdentityFrame
    host_capabilities: HostCapabilities
    channels: Mapping[str, object] | None = None


class HostDiscoveryProvider(Protocol):
    """Platform-neutral provider boundary for OS/device enumeration."""

    def enumerate_candidates(self) -> Iterable[HostDiscoveryCandidate]:
        ...


class MemoryHostDiscoveryProvider:
    """Deterministic reference provider for discovery conformance tests."""

    def __init__(self, candidates: Iterable[HostDiscoveryCandidate] = ()) -> None:
        self._candidates = tuple(candidates)

    def enumerate_candidates(self) -> tuple[HostDiscoveryCandidate, ...]:
        """Return the provider snapshot without exposing mutable state."""
        return self._candidates


class HostDeviceEnumerator:
    """Validate transport-neutral Coreless advertisements deterministically."""

    def discover(
        self, candidates: Iterable[HostDiscoveryCandidate]
    ) -> tuple[HostEndpoint, ...]:
        endpoints: dict[str, HostEndpoint] = {}
        for candidate in candidates:
            endpoint = self._decode(candidate)
            if endpoint.endpoint_id in endpoints:
                raise ValueError(
                    f"duplicate host endpoint id: {endpoint.endpoint_id}"
                )
            endpoints[endpoint.endpoint_id] = endpoint
        return tuple(endpoints[key] for key in sorted(endpoints))

    def discover_provider(
        self, provider: HostDiscoveryProvider
    ) -> tuple[HostEndpoint, ...]:
        """Enumerate candidates supplied by a platform adapter."""
        return self.discover(provider.enumerate_candidates())

    def _decode(self, candidate: HostDiscoveryCandidate) -> HostEndpoint:
        if not candidate.endpoint_id:
            raise ValueError("endpoint_id must not be empty")
        try:
            frame = (
                DeviceIdentityFrame.decode(candidate.identity_frame)
                if isinstance(candidate.identity_frame, bytes)
                else candidate.identity_frame
            )
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid Coreless discovery identity frame") from exc

        if not frame.is_coreless64():
            raise ValueError("unsupported Coreless discovery endpoint")
        if frame.protocol_version <= 0:
            raise ValueError("invalid Coreless discovery protocol version")
        try:
            computer_id = frame.payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("invalid Coreless discovery identity payload") from exc
        if not computer_id:
            raise ValueError("Coreless discovery identity is empty")

        return HostEndpoint(
            endpoint_id=candidate.endpoint_id,
            identity=CorelessIdentity(
                computer_id=computer_id,
                protocol_version=frame.protocol_version,
            ),
            capabilities=candidate.host_capabilities,
            channels=candidate.channels,
            device_capabilities=frame.capability_names(),
        )
