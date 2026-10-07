"""Reference host enumeration and transport adapters for Coreless.

These adapters model the host-side discovery/transport boundary without making
the host responsible for Coreless computation.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Mapping
from host_interface import CorelessHostInterface, CorelessIdentity, HostCapabilities
from device_command import CommandBatch, DeviceCommand, is_response, round_trip


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


@dataclass(frozen=True)
class HostTransportSession:
    """Bound transport state for one Coreless endpoint attachment."""

    endpoint: HostEndpoint
    interface: CorelessHostInterface
    negotiated: frozenset[str]

    @property
    def endpoint_id(self) -> str:
        return self.endpoint.endpoint_id

    @property
    def attached(self) -> bool:
        return self.interface.attached

    def channel(self, capability: str) -> object:
        """Return the channel bound to a negotiated session capability."""
        self.validate()
        return self.interface.channel(capability)

    def require_channels(self, capabilities: frozenset[str] | set[str]) -> None:
        """Require all requested session capabilities to have live channels."""
        self.validate()
        if not self.interface.transport_ready(capabilities):
            missing = sorted(
                capability
                for capability in capabilities
                if capability not in self.interface.channels
            )
            raise RuntimeError(
                f"host transport session channels are missing: {missing}"
            )

    def validate(self) -> None:
        """Ensure the session still refers to its original live attachment."""
        if not self.attached:
            raise RuntimeError("host transport session is detached")
        if self.interface.identity != self.endpoint.identity:
            raise RuntimeError("host transport session identity changed")
        if self.interface.negotiated != self.negotiated:
            raise RuntimeError("host transport session negotiation changed")


class HostTransportAdapter:
    def enumerate(self) -> tuple[HostEndpoint, ...]:
        raise NotImplementedError

    def connect(
        self,
        endpoint: HostEndpoint,
        interface: CorelessHostInterface,
        *,
        system=None,
    ) -> frozenset[str]:
        """Attach a host endpoint and optionally bind a persistent Coreless system."""
        negotiated = interface.attach_identity_frame(
            endpoint.identity_frame(), endpoint.capabilities, system=system
        )
        interface.clear_channels()
        for capability, channel in endpoint.channel_map().items():
            if capability in negotiated:
                interface.bind_channel(capability, channel)
        return negotiated

    def open_session(
        self,
        endpoint: HostEndpoint,
        interface: CorelessHostInterface,
        *,
        system=None,
    ) -> HostTransportSession:
        """Attach an endpoint and retain its negotiated transport session."""
        negotiated = self.connect(endpoint, interface, system=system)
        return HostTransportSession(endpoint, interface, negotiated)

    def exchange(
        self,
        endpoint: HostEndpoint,
        interface: CorelessHostInterface,
        frame: bytes,
    ) -> bytes:
        """Carry one encoded command frame across the transport boundary."""
        if not interface.attached:
            self.connect(endpoint, interface)
        elif interface.identity != endpoint.identity:
            raise ValueError("Coreless host endpoint identity mismatch")
        command = DeviceCommand.decode(frame)
        reply = interface.handle_command(round_trip(command))
        return reply.encode()

    def exchange_session(
        self,
        session: HostTransportSession,
        frame: bytes,
    ) -> bytes:
        """Exchange a wire frame through an established transport session."""
        session.validate()
        return self.exchange(session.endpoint, session.interface, frame)

    def exchange_batch(
        self,
        endpoint: HostEndpoint,
        interface: CorelessHostInterface,
        payload: bytes,
    ) -> bytes:
        """Carry an ordered command batch across the transport boundary."""
        if not interface.attached:
            self.connect(endpoint, interface)
        elif interface.identity != endpoint.identity:
            raise ValueError("Coreless host endpoint identity mismatch")
        batch = CommandBatch.decode(payload)
        replies = []
        for command in batch.commands:
            replies.append(interface.handle_command(round_trip(command)))
        return CommandBatch(tuple(replies)).encode()

    def exchange_session_batch(
        self,
        session: HostTransportSession,
        payload: bytes,
    ) -> bytes:
        """Exchange an ordered command batch through an established session."""
        session.validate()
        return self.exchange_batch(session.endpoint, session.interface, payload)

    def send_batch(
        self,
        endpoint: HostEndpoint,
        interface: CorelessHostInterface,
        batch: CommandBatch,
    ) -> CommandBatch:
        """Send an ordered command batch and validate every correlated response."""
        reply = CommandBatch.decode(
            self.exchange_batch(endpoint, interface, batch.encode())
        )
        if len(reply.commands) != len(batch.commands):
            raise ValueError("Coreless batch response count mismatch")
        for request, response in zip(batch.commands, reply.commands):
            if not is_response(response):
                raise ValueError("Coreless batch reply is not a response frame")
            if response.request_id != request.request_id:
                raise ValueError("Coreless batch response request id mismatch")
            if response.opcode != request.opcode:
                raise ValueError("Coreless batch response opcode mismatch")
        return reply

    def send_session_batch(
        self,
        session: HostTransportSession,
        batch: CommandBatch,
    ) -> CommandBatch:
        """Send a command batch through an established transport session."""
        reply = CommandBatch.decode(
            self.exchange_session_batch(session, batch.encode())
        )
        if len(reply.commands) != len(batch.commands):
            raise ValueError("Coreless session batch response count mismatch")
        for request, response in zip(batch.commands, reply.commands):
            if not is_response(response):
                raise ValueError("Coreless session batch reply is not a response frame")
            if response.request_id != request.request_id:
                raise ValueError("Coreless session batch response request id mismatch")
            if response.opcode != request.opcode:
                raise ValueError("Coreless session batch response opcode mismatch")
        return reply


    def send_command(
        self,
        endpoint: HostEndpoint,
        interface: CorelessHostInterface,
        command: DeviceCommand,
    ) -> DeviceCommand:
        """Carry a command and validate its correlated response."""
        reply_frame = self.exchange(endpoint, interface, command.encode())
        reply = DeviceCommand.decode(reply_frame)
        if not is_response(reply):
            raise ValueError("Coreless response is not a response frame")
        if reply.request_id != command.request_id:
            raise ValueError("Coreless response request id mismatch")
        if reply.opcode != command.opcode:
            raise ValueError("Coreless response opcode mismatch")
        return reply

    def send_session_command(
        self,
        session: HostTransportSession,
        command: DeviceCommand,
    ) -> DeviceCommand:
        """Send a command through an established transport session."""
        reply_frame = self.exchange_session(session, command.encode())
        reply = DeviceCommand.decode(reply_frame)
        if not is_response(reply):
            raise ValueError("Coreless session reply is not a response frame")
        if reply.request_id != command.request_id:
            raise ValueError("Coreless session response request id mismatch")
        if reply.opcode != command.opcode:
            raise ValueError("Coreless session response opcode mismatch")
        return reply

    def close_session(self, session: HostTransportSession) -> None:
        """Close the session while preserving the Coreless machine state."""
        self.disconnect(session.interface)

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

    def connect(
        self,
        endpoint: HostEndpoint,
        interface: CorelessHostInterface,
        *,
        system=None,
    ) -> frozenset[str]:
        current = self._endpoints.get(endpoint.endpoint_id)
        if current is None or current != endpoint:
            raise ValueError("unknown host endpoint")
        return super().connect(current, interface, system=system)
