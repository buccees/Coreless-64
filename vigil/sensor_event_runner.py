"""Serve normalized events generated from an explicit CSI JSONL sample file.

This runner does not capture Wi-Fi traffic or connect to hardware. Each input line
must contain already-obtained baseline/current CSI vectors and timestamps. It
processes those samples through the existing CSI pipeline, then exposes a
loopback-only, read-only event API.
"""
from __future__ import annotations

import argparse
import json
from http.server import HTTPServer
from pathlib import Path
from typing import Any, Sequence

from .csi_pipeline import CsiTelemetryPipeline
from .sensor_event import SensorEventLedger
from .sensor_event_adapter import csi_result_to_sensor_event
from .sensor_event_api import make_sensor_event_handler
from .telemetry_store import TelemetryStore


def _complex_vector(value: Any, field: str) -> tuple[complex, ...]:
    """Parse JSON numbers or [real, imag] pairs as a CSI complex vector."""
    if not isinstance(value, list) or not value:
        raise ValueError(f"{field} must be a non-empty array")
    result: list[complex] = []
    for index, item in enumerate(value):
        if isinstance(item, bool):
            raise ValueError(f"{field}[{index}] must be a number or [real, imag]")
        if isinstance(item, (int, float)):
            result.append(complex(item, 0.0))
        elif (
            isinstance(item, list) and len(item) == 2
            and all(isinstance(part, (int, float)) and not isinstance(part, bool) for part in item)
        ):
            result.append(complex(item[0], item[1]))
        else:
            raise ValueError(f"{field}[{index}] must be a number or [real, imag]")
    return tuple(result)


def load_csi_jsonl(path: str | Path, ledger: SensorEventLedger) -> int:
    """Process JSONL CSI samples in file order and append normalized events."""
    if not isinstance(ledger, SensorEventLedger):
        raise TypeError("ledger must be a SensorEventLedger")
    pipelines: dict[tuple[str, int], CsiTelemetryPipeline] = {}
    store = TelemetryStore()
    count = 0
    try:
        with Path(path).open("r", encoding="utf-8") as source:
            for line_number, raw in enumerate(source, start=1):
                if not raw.strip() or raw.lstrip().startswith("#"):
                    continue
                try:
                    row = json.loads(raw)
                    if not isinstance(row, dict):
                        raise ValueError("each line must be a JSON object")
                    sensor_id = row.get("sensor_id")
                    channel_mhz = row.get("channel_mhz")
                    timestamp_ns = row.get("timestamp_ns")
                    if not isinstance(sensor_id, str) or not sensor_id.strip():
                        raise ValueError("sensor_id must be a non-empty string")
                    if isinstance(channel_mhz, bool) or not isinstance(channel_mhz, int) or channel_mhz <= 0:
                        raise ValueError("channel_mhz must be a positive integer")
                    if isinstance(timestamp_ns, bool) or not isinstance(timestamp_ns, int) or timestamp_ns < 0:
                        raise ValueError("timestamp_ns must be a non-negative integer")
                    baseline = _complex_vector(row.get("baseline"), "baseline")
                    current = _complex_vector(row.get("current"), "current")
                    if len(baseline) != len(current):
                        raise ValueError("baseline and current must have equal lengths")
                    packet_length = row.get("packet_length", 0)
                    signal_dbm = row.get("signal_dbm")
                    key = (sensor_id, channel_mhz)
                    pipeline = pipelines.get(key)
                    if pipeline is None:
                        pipeline = CsiTelemetryPipeline(
                            sensor_id=sensor_id, channel_mhz=channel_mhz, store=store
                        )
                        pipelines[key] = pipeline
                    result = pipeline.process(
                        timestamp_ns=timestamp_ns,
                        baseline=baseline,
                        current=current,
                        packet_length=packet_length,
                        signal_dbm=signal_dbm,
                    )
                    ledger.append(csi_result_to_sensor_event(result))
                    count += 1
                except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
                    raise ValueError(f"{path}:{line_number}: {exc}") from exc
    finally:
        store.close()
    return count


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-jsonl", required=True, help="path to explicit CSI sample JSONL input")
    parser.add_argument("--host", default="127.0.0.1", help="bind address (loopback by default)")
    parser.add_argument("--port", type=int, default=8765, help="HTTP port (default: 8765; use 0 for an ephemeral port)")
    args = parser.parse_args(argv)
    if args.host not in {"127.0.0.1", "::1", "localhost"}:
        parser.error("refusing non-loopback bind; expose the feed only through a separately secured proxy")
    if not 0 <= args.port <= 65535:
        parser.error("--port must be between 0 and 65535")

    ledger = SensorEventLedger()
    try:
        count = load_csi_jsonl(args.input_jsonl, ledger)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    server = HTTPServer((args.host, args.port), make_sensor_event_handler(ledger))
    print(f"Loaded {count} supplied CSI samples; serving read-only events at http://{args.host}:{server.server_port}/events")
    print("INPUT MODE ONLY — no hardware capture; CSI events are context, not object positions.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\\nStopping VIGIL event feed.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
