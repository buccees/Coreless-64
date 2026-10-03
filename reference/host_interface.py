"""Plug-and-play external host boundary for a Coreless computer.

The host supplies external power/I/O transport. It is not the Coreless
computational owner.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class HostCapabilities:
    """Versioned capabilities offered by an external host."""

    protocol_version: int = 1
    display: bool = False
    input: bool = False
    network: bool = False
    startup: bool = False
    management: bool = False
    telemetry: bool = False

    def as_set(self) -> frozenset[str]:
        return frozenset(
            name
            for name, enabled in (
                ("display", self.display),
                ("input", self.input),
                ("network", self.network),
                ("startup", self.startup),
                ("management", self.management),
                ("telemetry", self.telemetry),
            )
            if enabled
        )


@dataclass(frozen=True)
class CorelessIdentity:
    """Stable identity advertised by a Coreless endpoint."""

    computer_id: str
    architecture: str = "Coreless-64"
    protocol_version: int = 1


class CorelessHostInterface:
    """Discovery, negotiation, attachment, and I/O boundary for a host."""

    VERSION = 1

    def __init__(
        self,
        identity: CorelessIdentity,
        *,
        supported: frozenset[str] | set[str] = frozenset(
            {"display", "input", "network", "startup"}
        ),
    ) -> None:
        if not identity.computer_id:
            raise ValueError("computer_id must not be empty")
        if identity.architecture != "Coreless-64":
            raise ValueError("unsupported Coreless architecture")
        self.identity = identity
        self.supported = frozenset(supported)
        self._host_capabilities: HostCapabilities | None = None
        self._negotiated = frozenset()
        self._attached = False
        self._channels: dict[str, object] = {}

    @property
    def attached(self) -> bool:
        return self._attached

    @property
    def negotiated(self) -> frozenset[str]:
        return self._negotiated

    @property
    def channels(self) -> Mapping[str, object]:
        return dict(self._channels)

    def discover(self) -> CorelessIdentity:
        """Advertise the Coreless identity before higher-level services."""
        return self.identity

    def verify(self, identity: CorelessIdentity) -> bool:
        """Verify architecture and protocol compatibility."""
        return (
            identity.computer_id == self.identity.computer_id
            and identity.architecture == self.identity.architecture
            and identity.protocol_version == self.VERSION
        )

    def negotiate(self, host: HostCapabilities) -> frozenset[str]:
        """Select only capabilities supported by both endpoints."""
        if host.protocol_version != self.VERSION:
            raise ValueError("unsupported host-interface protocol version")
        selected = host.as_set() & self.supported
        self._host_capabilities = host
        self._negotiated = frozenset(selected)
        return self._negotiated

    def attach(self, identity: CorelessIdentity, host: HostCapabilities) -> frozenset[str]:
        """Verify identity, negotiate capabilities, and attach the host."""
        if not self.verify(identity):
            raise ValueError("Coreless identity verification failed")
        negotiated = self.negotiate(host)
        self._attached = True
        return negotiated

    def bind_channel(self, capability: str, channel: object) -> None:
        """Bind an externally provided transport to a negotiated capability."""
        if not self._attached:
            raise RuntimeError("host interface is not attached")
        if capability not in self._negotiated:
            raise PermissionError(
                f"capability was not negotiated: {capability}"
            )
        self._channels[capability] = channel

    def channel(self, capability: str) -> object:
        """Return a bound external channel."""
        if capability not in self._channels:
            raise KeyError(f"no channel bound: {capability}")
        return self._channels[capability]

    def detach(self) -> None:
        """Close external channels without destroying Coreless state."""
        self._channels.clear()
        self._negotiated = frozenset()
        self._host_capabilities = None
        self._attached = False

    def status(self) -> dict[str, object]:
        return {
            "identity": {
                "computer_id": self.identity.computer_id,
                "architecture": self.identity.architecture,
                "protocol_version": self.identity.protocol_version,
            },
            "attached": self.attached,
            "negotiated": tuple(sorted(self.negotiated)),
            "channels": tuple(sorted(self._channels)),
        }
