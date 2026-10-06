"""Plug-and-play external host boundary for a Coreless computer.

The host supplies external power/I/O transport. It is not the Coreless
computational owner.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, TYPE_CHECKING

from device_protocol import (
    ARCHITECTURE_CORELESS64,
    DeviceIdentityFrame,
    capability_bits,
)

if TYPE_CHECKING:
    from system import CorelessSystem
    from components import CorelessHub
    from input import CorelessInputRouter


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
        self._input_router: CorelessInputRouter | None = None
        self._device_storage: dict[str, bytes] = {}

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

    def device_identity_frame(self) -> DeviceIdentityFrame:
        """Build the transport-neutral identity frame for plug-and-play discovery."""
        return DeviceIdentityFrame(
            protocol_version=self.identity.protocol_version,
            architecture=ARCHITECTURE_CORELESS64,
            device_type=1,
            capabilities=capability_bits(set(self.supported)),
            payload=self.identity.computer_id.encode("utf-8"),
        )

    def verify_identity_frame(self, frame: DeviceIdentityFrame) -> bool:
        """Verify a transport identity frame before host attachment."""
        try:
            return (
                frame.architecture == ARCHITECTURE_CORELESS64
                and frame.protocol_version == self.identity.protocol_version
                and frame.payload.decode("utf-8") == self.identity.computer_id
            )
        except UnicodeDecodeError:
            return False

    def attach_identity_frame(
        self,
        frame: DeviceIdentityFrame | bytes,
        host: HostCapabilities,
        *,
        system: CorelessSystem | None = None,
    ) -> frozenset[str]:
        """Decode and verify a transport identity frame, then attach the host."""
        decoded = DeviceIdentityFrame.decode(frame) if isinstance(frame, bytes) else frame
        if not self.verify_identity_frame(decoded):
            raise ValueError("Coreless transport identity verification failed")
        identity = CorelessIdentity(
            computer_id=decoded.payload.decode("utf-8"),
            protocol_version=decoded.protocol_version,
        )
        return self.attach(identity, host, system=system)

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

    def handle_command(self, command):
        """Dispatch a decoded device command to the attached Coreless system."""
        from device_command import (
            OP_CAPABILITIES, OP_EXECUTE, OP_READ, OP_STATUS, OP_SYNC, OP_WRITE,
            response,
        )
        if not self._attached:
            raise RuntimeError("host interface is not attached")
        if command.opcode == OP_CAPABILITIES:
            payload = "|".join(sorted(self._negotiated)).encode("utf-8")
            return response(command, payload)
        if command.opcode == OP_STATUS:
            return response(command, repr(self.status()).encode("utf-8"))
        if command.opcode == OP_SYNC:
            return response(command, b"ok")
        if command.opcode == OP_EXECUTE:
            if "compute" not in self.supported:
                return response(command, b"compute capability unavailable", error=True)
            if self._system is None and self._hub is None:
                return response(command, b"no Coreless system is bound", error=True)
            return response(command, b"execution endpoint ready")
        if command.opcode == OP_READ:
            try:
                key = command.payload.decode("utf-8")
                return response(command, self.device_read(key))
            except (UnicodeDecodeError, KeyError):
                return response(command, b"Coreless storage key unavailable", error=True)
        if command.opcode == OP_WRITE:
            try:
                if len(command.payload) < 2:
                    raise ValueError("storage write is missing key length")
                key_length = int.from_bytes(command.payload[:2], "little")
                key_end = 2 + key_length
                if key_end > len(command.payload):
                    raise ValueError("storage write key is truncated")
                key = command.payload[2:key_end].decode("utf-8")
                self.device_write(key, command.payload[key_end:])
                return response(command, b"ok")
            except (UnicodeDecodeError, ValueError, IndexError):
                return response(command, b"invalid Coreless storage write", error=True)
        return response(command, b"unsupported opcode", error=True)

    def bind_device_storage(self, storage: dict[str, bytes]) -> None:
        """Bind Coreless-owned key/value storage for device READ/WRITE commands."""
        if not self._attached:
            raise RuntimeError("host interface is not attached")
        if "storage" not in self.supported:
            raise PermissionError("storage capability is not supported")
        self._device_storage = storage
        self._channels["storage"] = storage

    def device_read(self, key: str) -> bytes:
        if key not in self._device_storage:
            raise KeyError(key)
        return bytes(self._device_storage[key])

    def device_write(self, key: str, data: bytes) -> None:
        if not key:
            raise ValueError("storage key must not be empty")
        self._device_storage[key] = bytes(data)

    @property
    def input_router(self) -> CorelessInputRouter | None:
        """Return the Coreless input router bound to the negotiated input channel."""
        return self._input_router

    def bind_input_router(self, router: CorelessInputRouter) -> None:
        """Bind Coreless-owned input routing after input transport negotiation."""
        if not self._attached:
            raise RuntimeError("host interface is not attached")
        if "input" not in self._negotiated:
            raise PermissionError("input capability was not negotiated")
        self._input_router = router
        self._channels["input"] = router

    def submit_input(self, event):
        """Submit a host input event through the Coreless input boundary."""
        if not self._attached:
            raise RuntimeError("host interface is not attached")
        if "input" not in self._negotiated:
            raise PermissionError("input capability was not negotiated")
        if self._input_router is None:
            raise RuntimeError("no Coreless input router is bound")
        return self._input_router.submit(event)

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

    def hub_checkpoint_status(self) -> dict[str, object]:
        """Expose coordinated checkpoint metadata through the host boundary."""
        if not self._attached:
            raise RuntimeError("host interface is not attached")
        if "management" not in self._negotiated:
            raise PermissionError("management capability was not negotiated")
        if self._hub is None:
            raise RuntimeError("no Coreless Hub is bound")

        key = f"machine/hub/{self._hub.hub_id}/checkpoint"
        components = []
        for component in self._hub.components():
            storage = getattr(
                getattr(component.system, "machine", None), "storage", None
            ) if component.system is not None else None
            present = storage is not None and key in getattr(storage, "objects", {})
            components.append(
                {"component_id": component.component_id, "manifest_present": present}
            )

        return {
            "hub_id": self._hub.hub_id,
            "checkpoint_key": key,
            "components": tuple(components),
            "committed": bool(components) and all(
                item["manifest_present"] for item in components
            ),
        }

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

    def required_channels(self, capabilities: frozenset[str] | set[str]) -> frozenset[str]:
        """Return negotiated capabilities that still need an external channel."""
        required = frozenset(capabilities)
        missing = required - self._negotiated
        if missing:
            raise PermissionError(
                f"capabilities were not negotiated: {sorted(missing)}"
            )
        return frozenset(capability for capability in required if capability not in self._channels)

    def transport_ready(self, capabilities: frozenset[str] | set[str]) -> bool:
        """Report whether all requested negotiated transports are bound."""
        return not self.required_channels(capabilities)

    def channel(self, capability: str) -> object:
        """Return a bound external channel."""
        if capability not in self._channels:
            raise KeyError(f"no channel bound: {capability}")
        return self._channels[capability]

    def detach(self) -> None:
        """Close external channels without destroying Coreless state."""
        self._channels.clear()
        self._input_router = None
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
            "input_router_bound": self._input_router is not None,
            "input_designated_device": (
                self._input_router.devices.designated_device_id
                if self._input_router is not None else None
            ),
            "input_bound_device": (
                self._input_router.devices.bound_device_id
                if self._input_router is not None else None
            ),
            "hub_component_count": len(self._hub.components()) if self._hub else 0,
            "hub_capabilities": tuple(sorted(self._hub.capabilities())) if self._hub else (),
        }
