"""Reference host enumeration and transport adapters for Coreless.

These adapters model the host-side discovery/transport boundary without making
the host responsible for Coreless computation.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Mapping
from host_interface import CorelessHostInterface, CorelessIdentity, HostCapabilities
from device_command import DeviceCommand, round_trip

@dataclass(frozen=True)
class HostEndpoint:
    endpoint_id: str
    identity: CorelessIdentity
    capabilities: HostCapabilities
    channels: Mapping[str, object] = ()
    device_capabilities: frozenset[str] | set[str] = frozenset(
        {"display", "input", "network", "startup"}
    )

    def identity_frame(self) -> bytes:
        """Return the wire-format identity advertisement for this endpoint."""
        interface = CorelessHostInterface(
            self.identity, supported=self.device_capabilities
        )
        return interface.device_identity_frame().encode()

    def channel_map(self) -> dict[str, object]:
        return dict(self.channels)

class HostTransportAdapter:
    def enumerate(self) -> tuple[HostEndpoint, ...]:
        raise NotImplementedError

    def connect(self, endpoint: HostEndpoint, interface: CorelessHostInterface) -> frozenset[str]:
        negotiated = interface.attach_identity_frame(
            endpoint.identity_frame(), endpoint.capabilities
        )
        for capability, channel in endpoint.channel_map().items():
            if capability in negotiated:
                interface.bind_channel(capability, channel)
        return negotiated

    def exchange(
        self,
        endpoint: HostEndpoint,
        interface: CorelessHostInterface,
        frame: bytes,
    ) -> bytes:
        """Carry one encoded command frame across the transport boundary."""
        if not interface.attached:
            self.connect(endpoint, interface)
        command = DeviceCommand.decode(frame)
        reply = interface.handle_command(round_trip(command))
        return reply.encode()

    def send_command(
        self,
        endpoint: HostEndpoint,
        interface: CorelessHostInterface,
        command: DeviceCommand,
    ) -> DeviceCommand:
        """Carry a command and its response across the wire boundary."""
        reply_frame = self.exchange(endpoint, interface, command.encode())
        return DeviceCommand.decode(reply_frame)

    def disconnect(self, interface: CorelessHostInterface) -> None:
        """End the active host attachment while preserving Coreless identity."""
        interface.detach()

class MemoryHostTransportAdapter(HostTransportAdapter):
    def __init__(self, endpoints: Iterable[HostEndpoint] = ()) -> None:
        self._endpoints = {endpoint.endpoint_id: endpoint for endpoint in endpoints}

    def register(self, endpoint: HostEndpoint) -> None:
        if not endpoint.endpoint_id:
            raise ValueError("endpoint_id must not be empty")
        self._endpoints[endpoint.endpoint_id] = endpoint

    def unregister(self, endpoint_id: str) -> None:
        self._endpoints.pop(endpoint_id, None)

    def enumerate(self) -> tuple[HostEndpoint, ...]:
        return tuple(self._endpoints[key] for key in sorted(self._endpoints))

    def connect(self, endpoint: HostEndpoint, interface: CorelessHostInterface) -> frozenset[str]:
        current = self._endpoints.get(endpoint.endpoint_id)
        if current is None or current != endpoint:
            raise ValueError("unknown host endpoint")
        return super().connect(current, interface)
