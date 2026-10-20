import importlib.util
import json
from pathlib import Path
import sys
import types

from arduino_io import encode_message


ROOT = Path(__file__).resolve().parents[1]
SMOKE_SCRIPT = ROOT / "scripts" / "arduino-smoke-test.py"
SPEC = importlib.util.spec_from_file_location("coreless_arduino_smoke_test", SMOKE_SCRIPT)
assert SPEC is not None and SPEC.loader is not None
smoke_test = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(smoke_test)


class FakeSerial:
    instance = None

    def __init__(self, port, *, baudrate, timeout, write_timeout):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.write_timeout = write_timeout
        self.writes = []
        self.reads = [encode_message("ack", "arduino-1", 8, {
            "request_sequence": 0,
            "op": "analog_read",
            "ok": True,
            "value": 512,
        })]
        FakeSerial.instance = self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def write(self, frame):
        self.writes.append(frame)
        return len(frame)

    def readline(self):
        return self.reads.pop(0) if self.reads else b""


def test_arduino_smoke_cli_sends_only_analog_read_and_checks_matching_ack(monkeypatch, capsys):
    fake_serial_module = types.ModuleType("serial")
    fake_serial_module.Serial = FakeSerial
    monkeypatch.setitem(sys.modules, "serial", fake_serial_module)
    monkeypatch.setattr(sys, "argv", [
        str(SMOKE_SCRIPT),
        "--port", "COM4",
        "--pin", "14",
        "--device-id", "arduino-1",
    ])

    assert smoke_test.main() == 0
    serial_port = FakeSerial.instance
    assert serial_port is not None
    assert len(serial_port.writes) == 1
    command = json.loads(serial_port.writes[0].decode("utf-8"))
    assert command["kind"] == "command"
    assert command["payload"]["op"] == "analog_read"
    assert command["payload"]["pin"] == 14
    assert "value" not in command["payload"]

    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "ok"
    assert output["device_id"] == "arduino-1"
    assert output["operation"] == "analog_read"
    assert output["value"] == 512
    assert output["request_sequence"] == 0
