import json
import pytest

from arduino_simulator import VirtualArduino


def command(sequence, op, pin=3, value=None, device_id="arduino-1", protocol=1):
    payload = {"op": op, "pin": pin}
    if value is not None:
        payload["value"] = value
    return json.dumps({
        "protocol": protocol,
        "kind": "command",
        "device_id": device_id,
        "sequence": sequence,
        "payload": payload,
    })


def decode(line):
    assert line.endswith(b"\n")
    return json.loads(line)


def test_valid_output_command_acknowledges_correlation_and_changes_state():
    device = VirtualArduino()
    reply = decode(device.process_line(command(1, "digital_write", value=1)))

    assert reply["kind"] == "ack"
    assert reply["payload"] == {
        "request_sequence": 1, "op": "digital_write", "ok": True
    }
    assert device.digital_outputs == {3: 1}


def test_sensor_event_is_deterministic_and_uses_device_sequence():
    device = VirtualArduino(analog_inputs={0: 417})

    first = decode(device.sensor_event())
    second = decode(device.sensor_event())

    assert first["payload"] == {"sensor": "analog", "pin": "A0", "value": 417}
    assert first["sequence"] == 0
    assert second["sequence"] == 1


@pytest.mark.parametrize(
    ("line", "message"),
    [
        ("not-json", "invalid JSON command"),
        ("[]", "invalid JSON command"),
        (json.dumps({"protocol": 2}), "unsupported protocol version"),
        (command(1, "digital_write", device_id="wrong"), "message kind or device identity mismatch"),
        (command(-1, "digital_write"), "invalid command sequence"),
        (command(1, "digital_write", pin=True, value=1), "invalid pin"),
        (command(1, "digital_write", value=2), "invalid digital value"),
        (command(1, "analog_write", value=256), "invalid analog value"),
        (command(1, "pin_mode", value="magic"), "invalid pin mode"),
        (command(1, "explode"), "unsupported operation"),
    ],
)
def test_invalid_commands_are_rejected_without_output_mutation(line, message):
    device = VirtualArduino()
    reply = decode(device.process_line(line))

    assert reply["kind"] == "error"
    assert reply["payload"]["message"] == message
    assert device.digital_outputs == {}
    assert device.analog_outputs == {}
    assert device.last_host_sequence == -1


def test_duplicate_and_out_of_order_commands_are_rejected():
    device = VirtualArduino()
    assert decode(device.process_line(command(7, "digital_write", value=1)))["kind"] == "ack"

    duplicate = decode(device.process_line(command(7, "digital_write", value=0)))
    old = decode(device.process_line(command(6, "digital_write", value=0)))

    assert duplicate["kind"] == old["kind"] == "error"
    assert duplicate["payload"]["message"] == "command sequence is not increasing"
    assert old["payload"]["message"] == "command sequence is not increasing"
    assert device.digital_outputs[3] == 1


def test_disconnect_sets_outputs_safe_and_blocks_io_until_reconnect():
    device = VirtualArduino()
    device.process_line(command(1, "digital_write", value=1))
    device.process_line(command(2, "analog_write", value=200))

    device.disconnect()

    assert device.connected is False
    assert device.digital_outputs == {3: 0}
    assert device.analog_outputs == {3: 0}
    with pytest.raises(RuntimeError, match="disconnected"):
        device.process_line(command(3, "digital_write", value=1))
    with pytest.raises(RuntimeError, match="disconnected"):
        device.sensor_event()


def test_reconnect_does_not_replay_stale_command_or_reset_sequence_guard():
    device = VirtualArduino()
    device.process_line(command(10, "digital_write", value=1))
    device.disconnect()
    device.reconnect()

    stale = decode(device.process_line(command(10, "digital_write", value=1)))
    fresh = decode(device.process_line(command(11, "digital_write", value=0)))

    assert stale["kind"] == "error"
    assert fresh["kind"] == "ack"
    assert device.digital_outputs[3] == 0


def test_oversized_command_is_rejected():
    device = VirtualArduino()
    reply = decode(device.process_line(" " * 256))

    assert reply["kind"] == "error"
    assert reply["payload"]["message"] == "command line too long"


def test_reads_return_configured_virtual_inputs():
    device = VirtualArduino(analog_inputs={3: 812}, digital_inputs={3: 1})

    digital = decode(device.process_line(command(1, "digital_read")))
    analog = decode(device.process_line(command(2, "analog_read")))

    assert digital["payload"]["value"] == 1
    assert analog["payload"]["value"] == 812
