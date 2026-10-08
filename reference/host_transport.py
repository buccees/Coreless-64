"""Reference host enumeration and transport adapters for Coreless.

These adapters model the host-side discovery/transport boundary without making
the host responsible for Coreless computation.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from typing import Iterable, Mapping
from host_interface import CorelessHostInterface, CorelessIdentity, HostCapabilities
from host_io import HostIO
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
        missing = sorted(
            capability
            for capability in capabilities
            if capability not in self.interface.channels
        )
        if missing:
            raise RuntimeError(
                f"host transport session channels are missing: {missing}"
            )
        closed = sorted(
            capability
            for capability in capabilities
            if HostTransportSession._channel_closed(self.interface.channels[capability])
        )
        if closed:
            raise RuntimeError(
                f"host transport session channels are closed: {closed}"
            )

    @staticmethod
    def _channel_closed(channel: object) -> bool:
        if bool(getattr(channel, "closed", False)):
            return True
        fileno = getattr(channel, "fileno", None)
        if callable(fileno):
            try:
                return fileno() < 0
            except (OSError, ValueError):
                return True
        return False

    def validate(self) -> None:
        """Ensure the session still refers to its original live attachment."""
        if not self.attached:
            raise RuntimeError("host transport session is detached")
        if self.interface.identity != self.endpoint.identity:
            raise RuntimeError("host transport session identity changed")
        if self.interface.negotiated != self.negotiated:
            raise RuntimeError("host transport session negotiation changed")
        closed = sorted(
            capability
            for capability in self.negotiated
            if capability in self.interface.channels
            and HostTransportSession._channel_closed(self.interface.channels[capability])
        )
        if closed:
            raise RuntimeError(
                f"host transport session channels are closed: {closed}"
            )


class HostTransportAdapter:
    def enumerate(self) -> tuple[HostEndpoint, ...]:
        raise NotImplementedError

    def discover(
        self, candidates
    ) -> tuple[HostEndpoint, ...]:
        """Turn transport-neutral identity advertisements into endpoints."""
        from host_discovery import HostDeviceEnumerator

        return HostDeviceEnumerator().discover(candidates)

    def discover_provider(self, provider) -> tuple[HostEndpoint, ...]:
        """Enumerate platform candidates through the neutral discovery contract."""
        from host_discovery import HostDeviceEnumerator

        return HostDeviceEnumerator().discover_provider(provider)

    def connect(
        self,
        endpoint: HostEndpoint,
        interface: CorelessHostInterface,
        *,
        system=None,
        host_io: HostIO | None = None,
        input_router=None,
    ) -> frozenset[str]:
        """Attach an endpoint, optionally binding its persistent system and host I/O."""
        if host_io is not None and not isinstance(host_io, HostIO):
            raise TypeError("host_io must implement the Coreless HostIO contract")

        # Validate the complete replacement bundle before mutating an existing
        # attachment. Reconnect failures must leave the current session intact.
        if host_io is not None:
            from host_io import DisplayTransport, InputTransport, NetworkTransport

            negotiated_preview = (
                interface.supported
                & endpoint.device_capabilities
                & endpoint.capabilities.as_set()
            )
            if "input" in negotiated_preview and input_router is None and interface.input_router is None:
                raise RuntimeError("input capability requires a Coreless input router")
            if input_router is not None and not hasattr(input_router, "submit"):
                raise TypeError("input_router must implement the Coreless input router contract")
            if "display" in negotiated_preview and not isinstance(host_io.display, DisplayTransport):
                raise TypeError("host display transport does not implement the Coreless display contract")
            if "input" in negotiated_preview and not isinstance(host_io.input, InputTransport):
                raise TypeError("host input transport does not implement the Coreless input contract")
            if "network" in negotiated_preview and not isinstance(host_io.network, NetworkTransport):
                raise TypeError("host network transport does not implement the Coreless network contract")

        # Snapshot the live attachment before any replacement mutation. The
        # identity layer is transactional on negotiation failure, but channel
        # binding and HostIO installation can also fail after that point.
        original_attached = interface._attached
        original_negotiated = interface._negotiated
        original_host_capabilities = interface._host_capabilities
        original_system = interface._system
        original_hub = interface._hub
        original_channels = dict(interface._channels)
        original_input_router = interface._input_router
        original_host_io = interface._host_io
        original_last_host_display = interface._last_host_display
        try:
            negotiated = interface.attach_identity_frame(
                endpoint.identity_frame(), endpoint.capabilities, system=system
            )
            interface.clear_channels()
            for capability, channel in endpoint.channel_map().items():
                if capability in negotiated:
                    interface.bind_channel(capability, channel)
            if host_io is not None:
                interface.bind_host_io(host_io, input_router=input_router)
            return negotiated
        except Exception:
            # Reconnects are transactional across the whole attachment
            # boundary: restore the previously live channels and HostIO if
            # any post-negotiation binding step fails.
            if original_attached:
                interface._attached = original_attached
                interface._negotiated = original_negotiated
                interface._host_capabilities = original_host_capabilities
                interface._system = original_system
                interface._hub = original_hub
                interface._channels = original_channels
                interface._input_router = original_input_router
                interface._host_io = original_host_io
                interface._last_host_display = original_last_host_display
            raise

    def open_session(
        self,
        endpoint: HostEndpoint,
        interface: CorelessHostInterface,
        *,
        system=None,
        host_io: HostIO | None = None,
        input_router=None,
    ) -> HostTransportSession:
        """Attach an endpoint and retain its negotiated transport session."""
        negotiated = self.connect(
            endpoint, interface, system=system, host_io=host_io, input_router=input_router
        )
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


class SocketHostTransportAdapter(HostTransportAdapter):
    """Host transport adapter using a connected socket network channel.

    Discovery remains provider-driven; the provider supplies endpoint identity
    and the connected socket through the endpoint's network channel.
    """

    def __init__(self, provider, *, max_packet_size: int | None = None) -> None:
        self._provider = provider
        self._max_packet_size = max_packet_size

    def enumerate(self) -> tuple[HostEndpoint, ...]:
        return self.discover_provider(self._provider)

    @property
    def provider(self):
        return self._provider

    @property
    def max_packet_size(self) -> int | None:
        """Return the configured maximum packet size for socket channels."""
        return self._max_packet_size

    def open_network(self, endpoint: HostEndpoint):
        """Return the connected socket transport advertised by an endpoint."""
        from host_socket import SocketNetworkTransport

        if not endpoint.capabilities.network:
            raise RuntimeError("host endpoint does not advertise network capability")
        channel = endpoint.channel_map().get("network")
        if channel is None:
            raise RuntimeError("host endpoint has no network channel")
        closed = bool(getattr(channel, "closed", False))
        if not closed:
            # Python's stdlib socket exposes closed state through fileno()
            # rather than a public .closed property. Keep the adapter neutral
            # for SocketNetworkTransport and socket-like test doubles while
            # rejecting a raw socket that has already been closed.
            fileno = getattr(channel, "fileno", None)
            if callable(fileno):
                try:
                    closed = fileno() < 0
                except (OSError, ValueError):
                    closed = True
        if closed:
            raise RuntimeError("host network channel is already closed")
        if self._max_packet_size is None:
            return SocketNetworkTransport(channel)
        return SocketNetworkTransport(channel, max_packet_size=self._max_packet_size)

    def connect(
        self,
        endpoint: HostEndpoint,
        interface: CorelessHostInterface,
        *,
        system=None,
        host_io: HostIO | None = None,
        input_router=None,
    ) -> frozenset[str]:
        """Attach the endpoint with its network channel wrapped by Coreless transport."""
        from host_socket import SocketNetworkTransport

        previous = interface.channels.get("network")
        was_attached = interface.attached
        original_negotiated = interface._negotiated
        original_host_capabilities = interface._host_capabilities
        original_system = interface._system
        original_hub = interface._hub
        original_channels = dict(interface._channels)
        original_input_router = interface._input_router
        original_host_io = interface._host_io
        original_last_host_display = interface._last_host_display
        network_transport = None
        if endpoint.capabilities.network:
            # A negotiated network capability must always have a concrete socket
            # channel. Validate and construct the replacement before mutating the
            # current attachment so a bad reconnect leaves the live session intact.
            if "network" not in endpoint.channel_map():
                raise RuntimeError("host endpoint has no network channel")
            network_transport = self.open_network(endpoint)
        shares_previous_socket = (
            isinstance(previous, SocketNetworkTransport)
            and network_transport is not None
            and previous.socket is network_transport.socket
        )
        try:
            negotiated = super().connect(
                endpoint,
                interface,
                system=system,
                host_io=host_io,
                input_router=input_router,
            )
        except Exception:
            # The replacement socket is not attached until the base connection
            # succeeds. Retire it if validation or attachment fails so a
            # failed reconnect cannot leak a live host socket. Cleanup failure
            # must never mask the original connection failure.
            if network_transport is not None and not shares_previous_socket:
                try:
                    network_transport.close()
                except Exception:
                    pass
            # A fresh attachment may have been partially established before
            # channel binding failed. Roll it back, but never destroy an
            # already-live attachment during a failed reconnect.
            if not was_attached and interface.attached:
                try:
                    interface.detach()
                except Exception:
                    pass
            raise
        if network_transport is not None:
            if "network" in negotiated:
                try:
                    interface.bind_channel("network", network_transport)
                except Exception:
                    if not shares_previous_socket:
                        try:
                            network_transport.close()
                        except Exception:
                            pass
                    # The base connection has already attached the interface.
                    # A network bind failure must preserve a previously live
                    # reconnect target just like any other post-attachment
                    # binding failure.
                    if was_attached:
                        interface._attached = was_attached
                        interface._negotiated = original_negotiated
                        interface._host_capabilities = original_host_capabilities
                        interface._system = original_system
                        interface._hub = original_hub
                        interface._channels = original_channels
                        interface._input_router = original_input_router
                        interface._host_io = original_host_io
                        interface._last_host_display = original_last_host_display
                    else:
                        try:
                            interface.detach()
                        except Exception:
                            pass
                    raise
            else:
                # The endpoint supplied a socket, but negotiation may decline
                # network support on the Coreless side. Do not leave that
                # newly-created transport live when it cannot be attached.
                network_transport.close()
        if isinstance(previous, SocketNetworkTransport) and previous is not network_transport:
            if network_transport is not None and previous.socket is network_transport.socket:
                # Reconnect created a new wrapper around the same host socket.
                # Retire the stale wrapper without closing the socket now owned
                # by the replacement wrapper.
                previous.retire_without_closing_socket()
            else:
                # The new attachment is already established. Failure to retire
                # the superseded socket must not roll back or mask a successful
                # reconnect; the transport's own close state records cleanup
                # failure without invalidating the new session.
                try:
                    previous.close()
                except Exception:
                    pass
        return negotiated

    def disconnect(self, interface: CorelessHostInterface) -> None:
        """Close socket transports before ending the host attachment."""
        channel = interface.channels.get("network")
        try:
            if channel is not None and hasattr(channel, "close"):
                channel.close()
        finally:
            # Detach even if the host socket reports a close error. The
            # transport boundary must never leave a stale Coreless attachment.
            super().disconnect(interface)


class ProviderHostTransportAdapter(HostTransportAdapter):
    """Reference adapter backed by a platform discovery provider.

    A concrete OS/device integration only needs to implement the
    HostDiscoveryProvider contract. Discovery and Coreless identity validation
    remain centralized in HostDeviceEnumerator.
    """

    def __init__(self, provider) -> None:
        self._provider = provider

    def enumerate(self) -> tuple[HostEndpoint, ...]:
        """Discover and validate the provider's current endpoint snapshot."""
        return self.discover_provider(self._provider)

    @property
    def provider(self):
        """Return the discovery provider without exposing adapter state."""
        return self._provider


class MemoryHostTransportAdapter(HostTransportAdapter):
    def __init__(self, endpoints: Iterable[HostEndpoint] = (), candidates=()) -> None:
        self._endpoints = {endpoint.endpoint_id: endpoint for endpoint in endpoints}
        self._candidates = list(candidates)

    def register_candidate(self, candidate) -> None:
        """Register a raw discovery candidate for later enumeration."""
        self._candidates.append(candidate)

    def enumerate_candidates(self) -> tuple[HostEndpoint, ...]:
        """Enumerate raw candidates through the platform-independent validator."""
        return self.discover(tuple(self._candidates))

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
        host_io=None,
        input_router=None,
    ) -> frozenset[str]:
        current = self._endpoints.get(endpoint.endpoint_id)
        if current is None or current != endpoint:
            raise ValueError("unknown host endpoint")
        return super().connect(
            current, interface, system=system, host_io=host_io, input_router=input_router
        )