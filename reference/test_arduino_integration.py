"""End-to-end protocol tests joining the Arduino bridge and virtual device."""
import sys
sys.path.insert(0, ".")

from arduino_io import ArduinoSerialIO, decode_message
from arduino_simulator import VirtualArduino


class VirtualSerialPort:
    """Minimal serial shim that feeds bridge writes into the virtual Arduino."""

    def __init__(self, device):
        self.device = device
        self.reads = []

    def write(self, data):
        self.reads.append(self.device.process_line(data))
        return len(data)

    def readline(self):
        if not self.reads:
            raise RuntimeError("no queued virtual serial response")
        return self.reads.pop(0)


def test_bridge_and_virtual_device_round_trip_commands_and_reads():
    device = VirtualArduino(analog_inputs={0: 417}, digital_inputs={7: 1})
    serial = VirtualSerialPort(device)
    bridge = ArduinoSerialIO(serial, device.device_id)

    assert bridge.send_command("digital_write", pin=13, value=1) == 0
    ack = bridge.receive_message()
    assert ack["kind"] == "ack"
    assert ack["payload"]["request_sequence"] == 0
    assert device.digital_outputs == {13: 1}

    assert bridge.send_command("analog_read", pin=0) == 1
    ack = bridge.receive_message()
    assert ack["kind"] == "ack"
    assert ack["payload"]["request_sequence"] == 1
    assert ack["payload"]["value"] == 417

    assert bridge.send_command("digital_read", pin=7) == 2
    assert bridge.receive_message()["payload"]["value"] == 1


def test_bridge_and_virtual_device_sensor_event_round_trip():
    device = VirtualArduino(analog_inputs={2: 612})
    serial = VirtualSerialPort(device)
    bridge = ArduinoSerialIO(serial, device.device_id)
    serial.reads.append(device.sensor_event(pin=2))

    event = bridge.receive_event()
    assert event["kind"] == "event"
    assert event["payload"] == {"sensor": "analog", "pin": "A2", "value": 612}


def test_disconnect_safe_state_and_reconnect_keep_command_sequence_guard():
    device = VirtualArduino()
    serial = VirtualSerialPort(device)
    bridge = ArduinoSerialIO(serial, device.device_id)

    bridge.send_command("digital_write", pin=13, value=1)
    assert bridge.receive_message()["kind"] == "ack"
    assert device.digital_outputs[13] == 1

    device.disconnect()
    assert device.digital_outputs[13] == 0

    device.reconnect()
    # The bridge advances its sequence only after a successful serial write.
    bridge.send_command("digital_write", pin=13, value=1)
    ack = bridge.receive_message()
    assert ack["kind"] == "ack"
    assert ack["payload"]["request_sequence"] == 1
    assert device.digital_outputs[13] == 1

    # Replaying the accepted command sequence directly must not change state.
    replay = decode_message(
        device.process_line(
            b'{"protocol":1,"kind":"command","device_id":"arduino-1",'
            b'"sequence":1,"payload":{"op":"digital_write","pin":13,"value":0}}\n'
        )
    )
    assert replay["kind"] == "error"
    assert replay["payload"]["message"] == "command sequence is not increasing"
    assert device.digital_outputs[13] == 1
