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


@pytest.mark.parametrize(
    "transport,method,message",
    [
        (MemoryDisplayTransport(), "send_frame", "display frame must be bytes-like"),
        (MemoryInputTransport(), "send_event", "input event must be bytes-like"),
        (MemoryNetworkTransport(), "send_packet", "network packet must be bytes-like"),
    ],
)
@pytest.mark.parametrize("invalid", [3, "not bytes", None])
def test_memory_transports_reject_non_bytes_payloads(transport, method, message, invalid):
    with pytest.raises(TypeError, match=message):
        getattr(transport, method)(invalid)


@pytest.mark.parametrize(
    "transport,method,receive",
    [
        (MemoryDisplayTransport(), "send_frame", "receive_frame"),
        (MemoryInputTransport(), "send_event", "receive_event"),
        (MemoryNetworkTransport(), "send_packet", "receive_packet"),
    ],
)
def test_memory_transports_normalize_bytes_like_payloads(transport, method, receive):
    payloads = [bytearray(b"mutable"), memoryview(b"view")]
    for payload in payloads:
        getattr(transport, method)(payload)
    assert [getattr(transport, receive)(), getattr(transport, receive)()] == [
        b"mutable", b"view"
    ]


@pytest.mark.parametrize("field,literal", [
    ("x", "1e999"),
    ("y", "-1e999"),
    ("pressure", "1e999"),
])
def test_decode_input_event_rejects_nonfinite_numeric_fields(field, literal):
    from host_io import decode_input_event

    base = (
        '{"abi_version":1,"event_type":"pointer_move","device_id":"mouse-1",'
        '"timestamp_ns":10,"sequence":1,"coordinate_frame":"coreless",'
        '"x":1.0,"y":2.0,"pressure":0.5,"metadata":{}}'
    )
    payload = base.replace(f'"{field}":' + {
        "x": "1.0",
        "y": "2.0",
        "pressure": "0.5",
    }[field], f'"{field}":{literal}').encode("utf-8")
    with pytest.raises(ValueError, match=f"{field} must be finite"):
        decode_input_event(payload)

@pytest.mark.parametrize("field,value", [
    ("x", float("nan")),
    ("pressure", float("inf")),
    ("metadata", {"nested": [float("-inf")]}),
])
def test_encode_input_event_rejects_non_string_metadata_keys():
    from host_io import encode_input_event
    from input import CoordinateFrame, InputEvent, InputEventType

    event = InputEvent(
        abi_version=1,
        event_type=InputEventType.POINTER_MOVE,
        device_id="mouse-1",
        timestamp_ns=10,
        sequence=1,
        coordinate_frame=CoordinateFrame.CORELESS,
        x=1.0,
        y=2.0,
        metadata={"nested": {1: "would be silently coerced by json"}},
    )
    with pytest.raises(ValueError, match="object keys must be strings"):
        encode_input_event(event)


def test_encode_input_event_rejects_nonfinite_numbers(field, value):
    from host_io import encode_input_event
    from input import CoordinateFrame, InputEvent, InputEventType

    fields = {
        "abi_version": 1,
        "event_type": InputEventType.POINTER_MOVE,
        "device_id": "mouse-1",
        "timestamp_ns": 10,
        "sequence": 1,
        "coordinate_frame": CoordinateFrame.CORELESS,
    }
    fields[field] = value
    if field == "x":
        fields["y"] = 2.0
    elif field == "metadata":
        fields["x"] = 1.0
        fields["y"] = 2.0
    event = InputEvent(**fields)
    with pytest.raises(ValueError):
        encode_input_event(event)


@pytest.mark.parametrize("literal", ["1e999", "-1e999"])
def test_decode_input_event_rejects_nonfinite_numbers_nested_in_metadata(literal):
    from host_io import decode_input_event

    payload = (
        '{"abi_version":1,"event_type":"pointer_move","device_id":"mouse-1",'
        '"timestamp_ns":10,"sequence":1,"coordinate_frame":"coreless",'
        '"metadata":{"nested":[{"reading":' + literal + '}]}}'
    ).encode("utf-8")
    with pytest.raises(ValueError, match="metadata"):
        decode_input_event(payload)


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_decode_input_event_rejects_nonstandard_json_numeric_constants(constant):
    from host_io import decode_input_event

    payload = (
        '{"abi_version":1,"event_type":"pointer_move","device_id":"mouse-1",'
        '"timestamp_ns":10,"sequence":1,"coordinate_frame":"coreless",'
        f'"x":{constant},"y":2,"metadata":{{}}' + "}"
    ).encode("utf-8")
    with pytest.raises(ValueError, match="invalid input event frame"):
        decode_input_event(payload)
