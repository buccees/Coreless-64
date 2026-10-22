"""Read-only local HTTP feed for normalized VIGIL sensor events.

The server is deliberately opt-in and loopback-only by default. It exposes
metadata already present in the event ledger; it does not acquire sensors.
"""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler
import json
from time import time_ns
from typing import Callable
from urllib.parse import parse_qs, urlsplit

from .sensor_event import SensorEventLedger


def make_sensor_event_handler(
    ledger: SensorEventLedger, *, clock_ns: Callable[[], int] = time_ns
) -> type[BaseHTTPRequestHandler]:
    """Build a GET-only handler for /health and /events."""
    if not isinstance(ledger, SensorEventLedger):
        raise TypeError("ledger must be a SensorEventLedger")

    class SensorEventHandler(BaseHTTPRequestHandler):
        server_version = "VIGIL-EventFeed/1.0"

        def _json(self, status: int, payload: dict) -> None:
            body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            parsed = urlsplit(self.path)
            if parsed.path == "/health":
                self._json(200, {"status": "ok", "feed": "read_only", "hardware_connected": False})
                return
            if parsed.path != "/events":
                self._json(404, {"error": "not_found"})
                return
            query = parse_qs(parsed.query, strict_parsing=False)
            try:
                limit = int(query.get("limit", ["100"])[0])
                max_age_raw = query.get("max_age_ns", [None])[0]
                max_age_ns = None if max_age_raw is None else int(max_age_raw)
                now_ns = clock_ns()
                events = ledger.snapshot(now_ns=now_ns, max_age_ns=max_age_ns, limit=limit)
            except (TypeError, ValueError, OverflowError) as exc:
                self._json(400, {"error": "invalid_query", "detail": str(exc)})
                return
            rows = []
            for event in events:
                row = event.to_dict()
                row["age_ns"] = now_ns - event.timestamp_ns
                row["freshness"] = "stale" if max_age_ns is not None and row["age_ns"] > max_age_ns else "current"
                row["alignment"] = ledger.alignment_for(event.event_id)
                rows.append(row)
            self._json(200, {
                "feed": "read_only",
                "generated_at_ns": now_ns,
                "count": len(rows),
                "events": rows,
            })

        def do_POST(self) -> None:
            self._json(405, {"error": "method_not_allowed", "read_only": True})

        def log_message(self, format: str, *args: object) -> None:
            # Avoid logging sensor identifiers or query strings by default.
            return

    return SensorEventHandler
