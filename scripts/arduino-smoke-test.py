#!/usr/bin/env python3
"""Read-only hardware smoke test for the Coreless-64 Arduino bridge.

The test sends exactly one analog_read command and waits for its matching ack.
It does not set pin modes or drive output pins. Install pyserial separately.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference"))

from arduino_io import ArduinoSerialIO  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True, help="Serial device, e.g. COM4 or /dev/ttyACM0")
    parser.add_argument("--pin", type=int, required=True, help="Board-specific numeric analog pin")
    parser.add_argument("--device-id", default="arduino-1", help="Expected firmware device identity")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--timeout", type=float, default=5.0, help="Overall acknowledgement timeout in seconds")
    args = parser.parse_args()

    if args.baud <= 0:
        parser.error("--baud must be positive")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if not 0 <= args.pin <= 255:
        parser.error("--pin must be in the protocol range 0..255")

    try:
        import serial
    except ImportError:
        print("pyserial is required; install it with: python -m pip install pyserial", file=sys.stderr)
        return 2

    try:
        with serial.Serial(args.port, baudrate=args.baud, timeout=min(0.25, args.timeout),
                           write_timeout=args.timeout) as port:
            bridge = ArduinoSerialIO(port, args.device_id)
            request_sequence = bridge.send_command("analog_read", pin=args.pin)
            deadline = time.monotonic() + args.timeout

            while time.monotonic() < deadline:
                remaining = deadline - time.monotonic()
                port.timeout = max(0.01, min(0.25, remaining))
                try:
                    message = bridge.receive_message()
                except TimeoutError:
                    continue

                if message["kind"] != "ack":
                    continue
                payload = message["payload"]
                if payload.get("request_sequence") != request_sequence:
                    continue
                if payload.get("op") != "analog_read" or payload.get("ok") is not True:
                    raise RuntimeError("Arduino returned an unexpected analog_read acknowledgement")
                value = payload.get("value")
                if isinstance(value, bool) or not isinstance(value, int):
                    raise RuntimeError("Arduino acknowledgement did not include an integer reading")

                print(json.dumps({
                    "status": "ok",
                    "device_id": args.device_id,
                    "operation": "analog_read",
                    "pin": args.pin,
                    "value": value,
                    "request_sequence": request_sequence,
                    "device_sequence": message["sequence"],
                }, sort_keys=True))
                return 0

        raise TimeoutError("no matching analog_read acknowledgement before deadline")
    except Exception as exc:
        print(f"Arduino smoke test failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
