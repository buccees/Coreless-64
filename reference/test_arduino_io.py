import json
import sys
sys.path.insert(0, ".")

import pytest

from arduino_io import (
    MAX_FRAME_BYTES,
    ArduinoInputAdapter,
    ArduinoSerialIO,
    decode_message,
    discover_serial_devices,
    encode_message,
)


class FakeSerial:
    def __init__(self):
        self.writes = []
        self.reads = []

    def write(self, data):
        self.writes.append(bytes(data))
        return len(data)

    def readline(self):
        if not self.reads:
            raise RuntimeError("no queued serial input")
        return self.reads.pop(0)


def frame(kind="event", device_id="arduino-1", sequence=0, payload=None):
    return encode_message(kind, device_id, sequence, payload or {})


def test_arduino_serial_io_encodes_digital_write_and_increments_sequence():
    serial = FakeSerial()
    bridge = ArduinoSerialIO(serial, "arduino-1")

    assert bridge.send_command("digital_write", pin=13, value=1) == 0
    assert bridge.send_command("analog_write", pin=9, value=127) == 1

    first = decode_message(serial.writes[0], expected_device_id="arduino-1")
    second = decode_message(serial.writes[1], expected_device_id="arduino-1")
    assert first["payload"] == {"op": "digital_write", "pin": 13, "value": 1}
    assert second["sequence"] == 1
    assert second["payload"]["value"] == 127


def test_arduino_serial_io_accepts_pin_mode_and_read_commands():
    serial = FakeSerial()
    bridge = ArduinoSerialIO(serial, "arduino-1")

    bridge.send_command("pin_mode", pin=4, value="input_pullup")
    bridge.send_command("analog_read", pin=2)

    assert decode_message(serial.writes[0])["payload"]["value"] == "input_pullup"
    assert decode_message(serial.writes[1])["payload"] == {"op": "analog_read", "pin": 2}


@pytest.mark.parametrize(
    ("operation", "pin", "value", "message"),
    [
        ("erase_all", 13, 1, "unsupported Arduino operation"),
        ("digital_write", -1, 1, "pin is out of range"),
        ("digital_write", 13, 2, "value is out of range"),
        ("analog_write", 9, 256, "value is out of range"),
        ("pin_mode", 4, "invalid", "pin_mode value is unsupported"),
        ("digital_read", 3, 1, "read operations do not accept a value"),
        ("digital_write", True, 1, "pin must be an integer"),
    ],
)
def test_arduino_serial_io_rejects_invalid_commands(operation, pin, value, message):
    bridge = ArduinoSerialIO(FakeSerial(), "arduino-1")
    with pytest.raises(ValueError, match=message):
        bridge.send_command(operation, pin=pin, value=value)


def test_arduino_serial_io_rejects_short_write_without_advancing_sequence():
    class ShortWrite(FakeSerial):
        def write(self, data):
            self.writes.append(bytes(data))
            if len(self.writes) == 1:
                return len(data) - 1
            return len(data)

    bridge = ArduinoSerialIO(ShortWrite(), "arduino-1")
    with pytest.raises(IOError, match="short write"):
        bridge.send_command("digital_write", pin=13, value=1)
    assert bridge.send_command("digital_write", pin=13, value=0) == 0


def test_arduino_serial_io_receives_sensor_event_and_checks_identity():
    serial = FakeSerial()
    serial.reads.append(frame(payload={"sensor": "temperature", "value": 23}))
    bridge = ArduinoSerialIO(serial, "arduino-1")

    message = bridge.receive_event()
    assert message["kind"] == "event"
    assert message["payload"]["value"] == 23

    serial.reads.append(frame(device_id="other-device", sequence=1))
    with pytest.raises(ValueError, match="identity mismatch"):
        bridge.receive_message()


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        (b"[]\n", "JSON object"),
        (b"not-json\n", "invalid Arduino JSON frame"),
        (b'{"protocol":1,"kind":"event","device_id":"x","sequence":0,"payload":{}}', "newline terminated"),
        (b'{"protocol":true,"kind":"event","device_id":"x","sequence":0,"payload":{}}\n', "protocol version"),
        (b'{"protocol":1,"kind":"event","device_id":"x","sequence":false,"payload":{}}\n', "sequence must be an integer"),
    ],
)
def test_arduino_decoder_rejects_malformed_frames(raw, message):
    with pytest.raises((TypeError, ValueError), match=message):
        decode_message(raw)


def test_arduino_decoder_enforces_frame_limit():
    raw = b'{"protocol":1,"kind":"event","device_id":"x","sequence":0,"payload":{"v":"' + b"a" * MAX_FRAME_BYTES + b'"}}\n'
    with pytest.raises(ValueError, match="maximum frame size"):
        decode_message(raw)


def test_arduino_serial_io_rejects_replayed_or_out_of_order_messages():
    serial = FakeSerial()
    serial.reads.extend([frame(sequence=3), frame(sequence=2)])
    bridge = ArduinoSerialIO(serial, "arduino-1")
    assert bridge.receive_event()["sequence"] == 3
    with pytest.raises(ValueError, match="not increasing"):
        bridge.receive_message()


def test_arduino_serial_io_separates_acknowledgements_from_events():
    serial = FakeSerial()
    serial.reads.append(frame(kind="ack", payload={"ok": True}))
    bridge = ArduinoSerialIO(serial, "arduino-1")
    assert bridge.receive_message()["kind"] == "ack"

    serial.reads.append(frame(kind="ack", sequence=1))
    with pytest.raises(ValueError, match="not an event"):
        bridge.receive_event()


def test_arduino_serial_io_surfaces_device_errors():
    serial = FakeSerial()
    serial.reads.append(frame(kind="error", payload={"message": "pin unavailable"}))
    bridge = ArduinoSerialIO(serial, "arduino-1")
    with pytest.raises(RuntimeError, match="pin unavailable"):
        bridge.receive_message()



def test_arduino_input_adapter_forwards_sensor_event_into_coreless_input_stream():
    from host_io import MemoryInputTransport, decode_input_event
    from input import CoordinateFrame, InputEventType

    serial = FakeSerial()
    serial.reads.append(frame(payload={"sensor": "analog", "pin": "A0", "value": 512}))
    bridge = ArduinoSerialIO(serial, "arduino-1")
    transport = MemoryInputTransport()
    adapter = ArduinoInputAdapter(bridge, transport)

    assert adapter.pump_once() is True
    event = decode_input_event(transport.receive_event())
    assert event.event_type is InputEventType.DEVICE_STATE
    assert event.device_id == "arduino-1"
    assert event.coordinate_frame is CoordinateFrame.HOST
    assert event.metadata["source"] == "arduino"
    assert event.metadata["payload"]["value"] == 512
    assert adapter.events_forwarded == 1


def test_arduino_input_adapter_maps_typed_pointer_event():
    from host_io import MemoryInputTransport, decode_input_event
    from input import InputEventType

    serial = FakeSerial()
    serial.reads.append(
        frame(payload={"event_type": "pointer_move", "x": 10.5, "y": 20, "button": None})
    )
    transport = MemoryInputTransport()
    adapter = ArduinoInputAdapter(ArduinoSerialIO(serial, "arduino-1"), transport)

    assert adapter.pump_once() is True
    event = decode_input_event(transport.receive_event())
    assert event.event_type is InputEventType.POINTER_MOVE
    assert event.x == 10.5
    assert event.y == 20.0


def test_arduino_input_adapter_consumes_ack_without_faking_input():
    from host_io import MemoryInputTransport

    serial = FakeSerial()
    serial.reads.append(frame(kind="ack", payload={"ok": True}))
    transport = MemoryInputTransport()
    adapter = ArduinoInputAdapter(ArduinoSerialIO(serial, "arduino-1"), transport)

    assert adapter.pump_once() is False
    assert adapter.acknowledgements_seen == 1
    assert not transport.events


def test_arduino_input_adapter_rejects_partial_coordinates():
    from host_io import MemoryInputTransport

    serial = FakeSerial()
    serial.reads.append(frame(payload={"event_type": "pointer_move", "x": 5}))
    adapter = ArduinoInputAdapter(ArduinoSerialIO(serial, "arduino-1"), MemoryInputTransport())

    with pytest.raises(ValueError, match="coordinates must include both"):
        adapter.pump_once()


def test_arduino_input_adapter_rejects_invalid_sensor_values():
    from host_io import MemoryInputTransport

    serial = FakeSerial()
    adapter = ArduinoInputAdapter(ArduinoSerialIO(serial, "arduino-1"), MemoryInputTransport())

    # Exercise the adapter's numeric validator with a JSON frame containing NaN.
    serial.reads.append(b'{"device_id":"arduino-1","kind":"event","payload":{"event_type":"pointer_move","x":NaN,"y":2},"protocol":1,"sequence":0}\n')
    with pytest.raises(ValueError, match="finite"):
        adapter.pump_once()



def test_serial_discovery_filters_and_sorts_without_opening_ports():
    from types import SimpleNamespace

    ports = [
        SimpleNamespace(device="/dev/ttyUSB1", description="other", hwid="usb:2", vid=0x2341, pid=0x0043, serial_number="B"),
        SimpleNamespace(device="/dev/ttyACM0", description="Arduino", hwid="usb:1", vid=0x2341, pid=0x0043, serial_number="A"),
        SimpleNamespace(device="/dev/ttyUSB0", description="different VID", hwid="usb:3", vid=0x9999, pid=0x0043, serial_number="C"),
    ]
    calls = []
    def provider():
        calls.append(True)
        return ports

    found = discover_serial_devices(
        provider, vendor_ids={0x2341}, product_ids={0x0043}
    )
    assert [item["device"] for item in found] == ["/dev/ttyACM0", "/dev/ttyUSB1"]
    assert found[0]["serial_number"] == "A"
    assert calls == [True]


def test_serial_discovery_can_select_one_stable_device():
    from types import SimpleNamespace

    ports = [
        SimpleNamespace(device="COM4", vid=1, pid=2, serial_number="first"),
        SimpleNamespace(device="COM3", vid=1, pid=2, serial_number="wanted"),
    ]
    found = discover_serial_devices(lambda: ports, serial_number="wanted")
    assert len(found) == 1
    assert found[0]["device"] == "COM3"


def test_serial_discovery_validates_provider_and_serial_filter():
    with pytest.raises(TypeError, match="provider must be callable"):
        discover_serial_devices(42)
    with pytest.raises(ValueError, match="serial_number"):
        discover_serial_devices(lambda: [], serial_number="  ")
