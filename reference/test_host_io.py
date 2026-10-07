import sys
sys.path.insert(0, ".")

import pytest

from host_io import (
    DisplayTransport,
    HostIO,
    InputTransport,
    MemoryDisplayTransport,
    MemoryHostIO,
    MemoryInputTransport,
    MemoryNetworkTransport,
    NetworkTransport,
)


@pytest.mark.parametrize(
    ("transport", "send", "receive", "payload"),
    [
        (MemoryDisplayTransport(), "send_frame", "receive_frame", b"frame"),
        (MemoryInputTransport(), "send_event", "receive_event", b"pointer"),
        (MemoryNetworkTransport(), "send_packet", "receive_packet", b"packet"),
    ],
)
def test_memory_host_transports_preserve_order_and_bytes(
    transport, send, receive, payload
):
    getattr(transport, send)(payload)
    getattr(transport, send)(payload + b"-2")
    assert getattr(transport, receive)() == payload
    assert getattr(transport, receive)() == payload + b"-2"


def test_memory_host_transports_reject_empty_receive():
    transports = (
        MemoryDisplayTransport(),
        MemoryInputTransport(),
        MemoryNetworkTransport(),
    )
    for transport in transports:
        with pytest.raises(RuntimeError):
            (
                transport.receive_frame()
                if isinstance(transport, MemoryDisplayTransport)
                else transport.receive_event()
                if isinstance(transport, MemoryInputTransport)
                else transport.receive_packet()
            )


def test_memory_host_io_bundles_independent_channels():
    io = MemoryHostIO()
    io.display.send_frame(b"frame")
    io.input.send_event(b"touch")
    io.network.send_packet(b"packet")

    assert io.display.receive_frame() == b"frame"
    assert io.input.receive_event() == b"touch"
    assert io.network.receive_packet() == b"packet"


def test_memory_transports_conform_to_neutral_protocols():
    display = MemoryDisplayTransport()
    input_transport = MemoryInputTransport()
    network = MemoryNetworkTransport()

    assert isinstance(display, DisplayTransport)
    assert isinstance(input_transport, InputTransport)
    assert isinstance(network, NetworkTransport)


def test_memory_host_io_conforms_to_neutral_bundle_protocol():
    assert isinstance(MemoryHostIO(), HostIO)


def test_host_io_bundle_rejects_invalid_negotiated_channel():
    from host_interface import CorelessHostInterface, CorelessIdentity, HostCapabilities

    class InvalidDisplayBundle:
        input = MemoryInputTransport()
        network = MemoryNetworkTransport()

        def __init__(self):
            self.display = object()

    interface = CorelessHostInterface(CorelessIdentity("invalid-channel"))
    interface.attach(
        CorelessIdentity("invalid-channel"),
        HostCapabilities(display=True, input=True, network=True),
    )

    with pytest.raises(TypeError, match="display transport"):
        class InputRouter:
        def submit(self, event):
            return event

    with pytest.raises(TypeError, match="display transport"):
        interface.bind_host_io(InvalidDisplayBundle(), input_router=InputRouter())

    assert "display" not in interface.channels
    assert "network" not in interface.channels
