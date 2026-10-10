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

    class InputRouter:
        def submit(self, event):
            return event

    with pytest.raises(TypeError, match="display transport"):
        interface.bind_host_io(InvalidDisplayBundle(), input_router=InputRouter())

    assert "display" not in interface.channels
    assert "network" not in interface.channels


def test_decode_input_event_rejects_non_object_and_malformed_frames():
    from host_io import decode_input_event

    for payload in (b"not json", b"\\xff", b"[]", b"null", b'"event"'):
        with pytest.raises(ValueError):
            decode_input_event(payload)


def test_decode_input_event_rejects_coercive_or_wrong_field_types():
    import json
    from host_io import decode_input_event

    base = {
        "abi_version": 1,
        "event_type": "pointer_move",
        "device_id": "mouse-1",
        "timestamp_ns": 10,
        "sequence": 1,
        "coordinate_frame": "coreless",
        "metadata": {},
    }
    cases = [
        {**base, "abi_version": "1"},
        {**base, "timestamp_ns": True},
        {**base, "sequence": 1.5},
        {**base, "device_id": 42},
        {**base, "metadata": []},
        {**base, "x": "10", "y": 20},
        {**base, "button": True},
    ]
    for value in cases:
        with pytest.raises((TypeError, ValueError)):
            decode_input_event(json.dumps(value).encode("utf-8"))


def test_decode_input_event_round_trips_encoded_event():
    from host_io import decode_input_event, encode_input_event
    from input import CoordinateFrame, InputEvent, InputEventType

    event = InputEvent(
        abi_version=1,
        event_type=InputEventType.TOUCH_BEGIN,
        device_id="touch-1",
        timestamp_ns=123,
        sequence=7,
        coordinate_frame=CoordinateFrame.CORELESS,
        x=1.5,
        y=2,
        contact_id=3,
        pressure=0.75,
        metadata={"source": "host"},
    )
    assert decode_input_event(encode_input_event(event)) == event


def test_memory_transport_empty_signal_is_specific():
    from host_io import HostIOQueueEmpty

    with pytest.raises(HostIOQueueEmpty):
        MemoryInputTransport().receive_event()
