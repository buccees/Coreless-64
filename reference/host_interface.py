"""Plug-and-play external host boundary for a Coreless computer.

The host supplies external power/I/O transport. It is not the Coreless
computational owner.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, TYPE_CHECKING

from host_io import HostIO, HostIOQueueEmpty, DisplayTransport, InputTransport, NetworkTransport
from device_protocol import (
    ARCHITECTURE_CORELESS64,
    DEVICE_TYPE_CORELESS64,
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
        self._host_io: object | None = None
        self._last_host_display: bytes | None = None

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
            device_type=DEVICE_TYPE_CORELESS64,
            capabilities=capability_bits(set(self.supported)),
            payload=self.identity.computer_id.encode("utf-8"),
        )

    def verify_identity_frame(self, frame: DeviceIdentityFrame) -> bool:
        """Verify a transport identity frame before host attachment."""
        try:
            return (
                frame.architecture == ARCHITECTURE_CORELESS64
                and frame.device_type == DEVICE_TYPE_CORELESS64
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
        try:
            if isinstance(frame, bytes):
                decoded = DeviceIdentityFrame.decode(frame)
            elif isinstance(frame, DeviceIdentityFrame):
                # Validate object inputs against the same strict wire contract.
                decoded = DeviceIdentityFrame.decode(frame.encode())
            else:
                raise TypeError("identity frame must be bytes or DeviceIdentityFrame")
        except ValueError as exc:
            if str(exc) == "unsupported Coreless device type":
                raise ValueError("Coreless transport identity verification failed") from exc
            raise
        if not self.verify_identity_frame(decoded):
            raise ValueError("Coreless transport identity verification failed")
        identity = CorelessIdentity(
            computer_id=decoded.payload.decode("utf-8"),
            protocol_version=decoded.protocol_version,
        )
        # The identity frame is the device-side capability advertisement.
        # Do not negotiate a host service that the attached Coreless endpoint
        # did not advertise on the transport.
        advertised = decoded.capability_names()
        negotiated_supported = self.supported & advertised
        original_supported = self.supported
        original_attached = self._attached
        original_negotiated = self._negotiated
        original_host_capabilities = self._host_capabilities
        original_system = self._system
        try:
            self.supported = frozenset(negotiated_supported)
            return self.attach(identity, host, system=system)
        except Exception:
            # Reconnect identity validation/negotiation is transactional:
            # restore the live attachment if the replacement cannot complete.
            self._attached = original_attached
            self._negotiated = original_negotiated
            self._host_capabilities = original_host_capabilities
            self._system = original_system
            raise
        finally:
            self.supported = original_supported

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
            decode_storage_write, response,
        )
        if not self._attached:
            raise RuntimeError("host interface is not attached")
        if command.opcode == OP_CAPABILITIES:
            payload = "|".join(sorted(self._negotiated)).encode("utf-8")
            return response(command, payload)
        if command.opcode == OP_STATUS:
            return response(command, repr(self.status()).encode("utf-8"))
        if command.opcode == OP_SYNC:
            if self._hub is not None:
                self._hub.machine.save_state()
            elif self._system is not None:
                self._system.machine.save_state()
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
                key, data = decode_storage_write(command.payload)
                self.device_write(key, data)
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

    def bind_host_io(self, host_io: HostIO, *, input_router: CorelessInputRouter | None = None) -> None:
        """Bind a validated host I/O bundle to the Coreless devices."""
        if not isinstance(host_io, HostIO):
            raise TypeError("host_io must implement the Coreless HostIO contract")
        if not self._attached:
            raise RuntimeError("host interface is not attached")
        if "input" in self._negotiated and input_router is None and self._input_router is None:
            raise RuntimeError("input capability requires a Coreless input router")
        if input_router is not None and not hasattr(input_router, "submit"):
            raise TypeError("input_router must implement the Coreless input router contract")

        # Validate the complete negotiated bundle before mutating any channels.
        # A partially attached host I/O bundle must never be observable.
        if "display" in self._negotiated:
            if not isinstance(host_io.display, DisplayTransport):
                raise TypeError("host display transport does not implement the Coreless display contract")
        if "input" in self._negotiated and not isinstance(host_io.input, InputTransport):
            raise TypeError("host input transport does not implement the Coreless input contract")
        if "network" in self._negotiated and not isinstance(host_io.network, NetworkTransport):
            raise TypeError("host network transport does not implement the Coreless network contract")

        original_channels = dict(self._channels)
        original_input_router = self._input_router
        original_host_io = self._host_io
        original_last_host_display = self._last_host_display
        try:
            if "display" in self._negotiated:
                self.bind_channel("display", host_io.display)
            if "network" in self._negotiated:
                self.bind_channel("network", host_io.network)
            if "input" in self._negotiated:
                if input_router is not None:
                    self.bind_input_router(input_router)
                self._channels["input"] = host_io.input
            self._host_io = host_io
            self._last_host_display = None
        except Exception:
            self._channels = original_channels
            self._input_router = original_input_router
            self._host_io = original_host_io
            self._last_host_display = original_last_host_display
            raise

    @property
    def host_io(self):
        """Return the currently bound concrete host I/O bundle."""
        return self._host_io

    def pump_host_io(self) -> dict[str, int]:
        """Move external I/O between host transports and Coreless devices."""
        if not self._attached:
            raise RuntimeError("host interface is not attached")
        if self._host_io is None:
            raise RuntimeError("no host I/O is bound")
        counts = {"display": 0, "input": 0, "network_rx": 0, "network_tx": 0}

        if "input" in self._negotiated:
            from host_io import decode_input_event
            while True:
                try:
                    payload = self._host_io.input.receive_event()
                except HostIOQueueEmpty:
                    break
                event = decode_input_event(payload)
                self.submit_input(event)
                if self._system is not None:
                    self._system.machine.graphics.input(event)
                counts["input"] += 1

        if "network" in self._negotiated:
            while True:
                try:
                    packet = self._host_io.network.receive_packet()
                except HostIOQueueEmpty:
                    break
                if not isinstance(packet, (bytes, bytearray, memoryview)):
                    raise TypeError("host network packet must be bytes-like")
                packet = bytes(packet)
                if self._system is not None:
                    self._system.machine.network.receive(packet)
                counts["network_rx"] += 1

            if self._system is not None:
                while self._system.machine.network.tx:
                    # Keep the packet queued until the transport confirms the
                    # complete send. A disconnect must not silently discard
                    # Coreless-owned outbound data.
                    packet = self._system.machine.network.tx[0]
                    self._host_io.network.send_packet(packet.data)
                    self._system.machine.network.tx.pop(0)
                    counts["network_tx"] += 1

        if "display" in self._negotiated and self._system is not None:
            surface = self._system.machine.graphics.scanout
            if surface is not None and surface.ready:
                frame = bytes(surface.pixels)
                if frame != self._last_host_display:
                    self._host_io.display.send_frame(frame)
                    self._last_host_display = frame
                    counts["display"] += 1

        return counts

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

    def clear_channels(self) -> None:
        """Remove all externally bound channels without detaching Coreless state."""
        self._channels.clear()
        self._input_router = None
        self._host_io = None
        self._last_host_display = None

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
        self._host_io = None
        self._last_host_display = None
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
