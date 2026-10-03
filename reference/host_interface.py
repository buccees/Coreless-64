"""Plug-and-play external host boundary for a Coreless computer.

The host supplies external power/I/O transport. It is not the Coreless
computational owner.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, TYPE_CHECKING

if TYPE_CHECKING:
    from system import CorelessSystem
    from components import CorelessHub


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
        self._system: CorelessSystem | None = None
        self._hub: CorelessHub | None = None

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

    def attach(
        self,
        identity: CorelessIdentity,
        host: HostCapabilities,
        *,
        system: CorelessSystem | None = None,
    ) -> frozenset[str]:
        """Verify identity, negotiate capabilities, and attach the host.

        An optional CorelessSystem binds the host to the persistent Coreless
        computer lifecycle. Detaching releases host channels only.
        """
        if not self.verify(identity):
            raise ValueError("Coreless identity verification failed")
        negotiated = self.negotiate(host)
        self._attached = True
        if system is not None:
            self.attach_system(system)
        return negotiated

    @property
    def system(self) -> CorelessSystem | None:
        return self._system

    @property
    def hub(self) -> CorelessHub | None:
        return self._hub

    def attach_hub(self, hub: CorelessHub) -> None:
        """Bind the host boundary to a Coreless Hub composition."""
        if not self._attached:
            raise RuntimeError("host interface is not attached")
        self._hub = hub

    def hub_components(self) -> tuple[object, ...]:
        """Return the currently composed autonomous Coreless components."""
        if self._hub is None:
            raise RuntimeError("no Coreless Hub is bound")
        return self._hub.components()

    def hub_capabilities(self) -> frozenset[str]:
        """Return the capabilities advertised by the unified Coreless system."""
        if self._hub is None:
            raise RuntimeError("no Coreless Hub is bound")
        return self._hub.capabilities()

    def attach_system(self, system: CorelessSystem) -> None:
        """Bind an already attached host to a persistent Coreless system."""
        if not self._attached:
            raise RuntimeError("host interface is not attached")
        self._system = system

    def boot(self, init_path: str = "/init"):
        """Boot or resume the bound Coreless computer through the host."""
        if not self._attached:
            raise RuntimeError("host interface is not attached")
        if "startup" not in self._negotiated:
            raise PermissionError("startup capability was not negotiated")
        if self._hub is not None:
            return self._hub.boot(init_path)
        if self._system is None:
            raise RuntimeError("no Coreless system is bound")
        return self._system.boot(init_path)

    def boot_hub(self, init_path: str = "/init"):
        """Boot the unified Coreless Hub composition through the host boundary."""
        if not self._attached:
            raise RuntimeError("host interface is not attached")
        if "startup" not in self._negotiated:
            raise PermissionError("startup capability was not negotiated")
        if self._hub is None:
            raise RuntimeError("no Coreless Hub is bound")
        return self._hub.boot(init_path)

    def resume(self):
        """Resume the persistent Coreless system using its saved boot manifest."""
        if self._hub is not None:
            return self._hub.resume()
        if self._system is None or self._system.boot_manifest is None:
            raise RuntimeError("no resumable Coreless system is bound")
        return self.boot(str(self._system.boot_manifest.get("init", "/init")))

    def shutdown(self):
        """Explicitly shut down the bound Coreless system; detach does not."""
        if self._hub is not None:
            return self._hub.shutdown()
        if self._system is None:
            raise RuntimeError("no Coreless system is bound")
        return self._system.shutdown()

    def checkpoint_hub(self, name: str = "hub"):
        """Create a coordinated checkpoint of the unified Coreless Hub."""
        if not self._attached:
            raise RuntimeError("host interface is not attached")
        if "management" not in self._negotiated:
            raise PermissionError("management capability was not negotiated")
        if self._hub is None:
            raise RuntimeError("no Coreless Hub is bound")
        return self._hub.checkpoint(name)

    def restore_hub(self, name: str = "hub"):
        """Restore the unified Coreless Hub from a coordinated checkpoint."""
        if not self._attached:
            raise RuntimeError("host interface is not attached")
        if "management" not in self._negotiated:
            raise PermissionError("management capability was not negotiated")
        if self._hub is None:
            raise RuntimeError("no Coreless Hub is bound")
        return self._hub.restore(name)

    def shutdown_hub(self):
        """Shut down the unified Coreless Hub composition through the host boundary."""
        if not self._attached:
            raise RuntimeError("host interface is not attached")
        if "startup" not in self._negotiated:
            raise PermissionError("startup capability was not negotiated")
        if self._hub is None:
            raise RuntimeError("no Coreless Hub is bound")
        return self._hub.shutdown()

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
            "system_bound": self._system is not None,
            "system_booted": bool(self._system and self._system.machine.booted),
            "hub_bound": self._hub is not None,
            "hub_component_count": len(self._hub.components()) if self._hub else 0,
            "hub_capabilities": tuple(sorted(self._hub.capabilities())) if self._hub else (),
        }
