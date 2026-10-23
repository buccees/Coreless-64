"""Minimal read-only WSGI endpoint for the remote operator display.

The hosting application must supply authentication/authorization and a live
CorelessSystem instance. This adapter exposes one GET-only JSON snapshot; it
never accepts commands and never invents sensor telemetry.
"""
from __future__ import annotations

import time
from dataclasses import replace
from threading import Lock
from typing import Callable, Iterable, Mapping, Any, Sequence
from urllib.parse import urlsplit

from operator_display import OperatorAlert, OperatorSensorStatus, OperatorViewState

START_RESPONSE = Callable[[str, list[tuple[str, str]]], Any]
Environ = Mapping[str, Any]
Authorizer = Callable[[Environ], bool]
SnapshotProvider = Callable[[], OperatorViewState]


def _is_https_origin(origin: object) -> bool:
    """Accept only serialized HTTPS origins, never URLs with paths or credentials."""
    if not isinstance(origin, str) or not origin or origin != origin.strip():
        return False
    try:
        parsed = urlsplit(origin)
        # A browser Origin header serializes scheme + authority only.
        return (
            parsed.scheme == "https"
            and bool(parsed.hostname)
            and parsed.username is None
            and parsed.password is None
            and parsed.path == ""
            and parsed.query == ""
            and parsed.fragment == ""
            and not parsed.netloc.endswith(":")
            and not any(char.isspace() for char in parsed.netloc)
            and "\\" not in parsed.netloc
            and (parsed.port is None or 1 <= parsed.port <= 65535)
            and origin == f"https://{parsed.netloc}"
        )
    except ValueError:
        return False


def coreless_view_state(system: Any, *, sequence: int = 0) -> OperatorViewState:
    """Build a truthful base snapshot from an existing CorelessSystem."""
    now_ns = time.time_ns()
    machine = getattr(system, "machine", None)
    booted = bool(getattr(machine, "booted", False))
    status_reader = getattr(system, "status", None)
    if not callable(status_reader):
        raise TypeError("system must expose CorelessSystem.status()")
    status_reader()
    return OperatorViewState(
        sequence=sequence,
        generated_at_ns=now_ns,
        source_timestamp_ns=now_ns,
        connection_state="connected",
        runtime_state="ready" if booted else "starting",
    )


class CorelessOperatorSnapshotProvider:
    """Thread-safe lifecycle snapshot provider; no fabricated sensor data."""

    def __init__(self, system: Any) -> None:
        if not callable(getattr(system, "status", None)):
            raise TypeError("system must expose CorelessSystem.status()")
        self._system = system
        self._sequence = 0
        self._lock = Lock()

    def __call__(self) -> OperatorViewState:
        with self._lock:
            sequence = self._sequence
            self._sequence += 1
        return coreless_view_state(self._system, sequence=sequence)


def create_coreless_operator_app(
    system: Any, *, authorize: Authorizer,
    path: str = "/api/operator/state",
    allowed_origins: Sequence[str] = (),
) -> "OperatorTelemetryApp":
    """Bind an existing CorelessSystem to an explicitly authorized WSGI app.

    Cross-origin browser access is disabled unless HTTPS origins are explicitly
    allowlisted. Production authentication and HTTPS remain host responsibilities.
    """
    provider = CorelessOperatorSnapshotProvider(system)
    return OperatorTelemetryApp(
        provider, authorize=authorize, path=path,
        allowed_origins=allowed_origins,
    )



class VigilSensorEventSnapshotProvider:
    """Combine Coreless lifecycle state with observed VIGIL ledger events.

    This reports only events already present in the injected ledger. It does not
    start sensors, imply physical hardware is connected, or turn context evidence
    into a location. A recent rejected/warning event marks that source degraded.
    """

    def __init__(self, system: Any, ledger: Any, *, stale_after_ns: int = 5_000_000_000) -> None:
        if not callable(getattr(system, "status", None)):
            raise TypeError("system must expose CorelessSystem.status()")
        if not callable(getattr(ledger, "snapshot", None)) or not callable(getattr(ledger, "alignment_for", None)):
            raise TypeError("ledger must expose snapshot() and alignment_for()")
        if isinstance(stale_after_ns, bool) or not isinstance(stale_after_ns, int) or stale_after_ns < 0:
            raise ValueError("stale_after_ns must be a non-negative integer")
        self._system = system
        self._ledger = ledger
        self._stale_after_ns = stale_after_ns
        self._sequence = 0
        self._lock = Lock()

    def __call__(self) -> OperatorViewState:
        with self._lock:
            sequence = self._sequence
            self._sequence += 1
        base = coreless_view_state(self._system, sequence=sequence)
        now_ns = base.generated_at_ns
        events = self._ledger.snapshot(now_ns=now_ns, limit=10_000)
        latest_by_sensor = {}
        for event in events:
            previous = latest_by_sensor.get(event.sensor_id)
            aligned = self._ledger.alignment_for(event.event_id)["aligned_timestamp_ns"]
            previous_aligned = (
                self._ledger.alignment_for(previous.event_id)["aligned_timestamp_ns"]
                if previous is not None else -1
            )
            if aligned > previous_aligned:
                latest_by_sensor[event.sensor_id] = event

        sensors = []
        alerts = []
        newest_source_ns = base.source_timestamp_ns
        for sensor_id, event in sorted(latest_by_sensor.items()):
            aligned_ns = self._ledger.alignment_for(event.event_id)["aligned_timestamp_ns"]
            age_ns = max(0, now_ns - aligned_ns)
            status = event.status.value
            if age_ns > self._stale_after_ns:
                sensor_state = "stale"
                reason = f"Last observed event is {age_ns} ns old; latest event: {event.reason}"
            elif status in {"rejected", "warning"}:
                sensor_state = "degraded"
                reason = event.reason
            else:
                sensor_state = "ready"
                reason = f"{status}: {event.reason}"
            sensors.append(OperatorSensorStatus(
                sensor_id=sensor_id,
                modality=event.modality,
                state=sensor_state,
                source_timestamp_ns=aligned_ns,
                calibration=event.calibration_status,
                reason=reason,
            ))
            newest_source_ns = max(newest_source_ns, aligned_ns)
            if status in {"rejected", "warning"}:
                alerts.append(OperatorAlert(
                    alert_id=event.event_id,
                    severity="warning",
                    message=f"{sensor_id}: {event.event_kind} — {event.reason}",
                    source="vigil.sensor_event",
                    source_timestamp_ns=aligned_ns,
                ))
        return replace(
            base,
            source_timestamp_ns=newest_source_ns,
            sensors=tuple(sensors),
            alerts=tuple(alerts),
        )

class OperatorTelemetryApp:
    """Authenticated, read-only WSGI endpoint with optional strict CORS allowlist."""

    def __init__(
        self,
        snapshot_provider: SnapshotProvider,
        *,
        authorize: Authorizer,
        path: str = "/api/operator/state",
        allowed_origins: Sequence[str] = (),
    ) -> None:
        if not callable(snapshot_provider):
            raise TypeError("snapshot_provider must be callable")
        if not callable(authorize):
            raise TypeError("authorize callback is required")
        if not path.startswith("/") or path == "/":
            raise ValueError("path must be a non-root absolute path")
        origins = tuple(allowed_origins)
        if any(not _is_https_origin(origin) for origin in origins):
            raise ValueError("allowed_origins must contain valid HTTPS origins only")
        if len(set(origins)) != len(origins):
            raise ValueError("allowed_origins must be unique")
        self._snapshot_provider = snapshot_provider
        self._authorize = authorize
        self._allowed_origins = frozenset(origins)
        self.path = path

    def _respond(
        self, start_response: START_RESPONSE, status: str, body: bytes,
        *, origin: str | None = None, preflight: bool = False,
    ):
        headers = [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(body))),
            ("Cache-Control", "no-store"),
            ("X-Content-Type-Options", "nosniff"),
            ("Vary", "Cookie, Authorization, Origin"),
        ]
        if origin is not None:
            headers.extend([
                ("Access-Control-Allow-Origin", origin),
                ("Access-Control-Allow-Credentials", "true"),
            ])
        if preflight:
            headers.extend([
                ("Access-Control-Allow-Methods", "GET, OPTIONS"),
                ("Access-Control-Allow-Headers", "Accept"),
                ("Access-Control-Max-Age", "300"),
            ])
        start_response(status, headers)
        return [body]

    def __call__(self, environ: Environ, start_response: START_RESPONSE) -> Iterable[bytes]:
        if environ.get("PATH_INFO") != self.path:
            return self._respond(start_response, "404 Not Found",
                                 b'{"error":"not_found"}')
        origin = environ.get("HTTP_ORIGIN")
        if origin and origin not in self._allowed_origins:
            return self._respond(start_response, "403 Forbidden",
                                 b'{"error":"origin_not_allowed"}')
        cors_origin = origin if origin in self._allowed_origins else None
        method = environ.get("REQUEST_METHOD", "GET").upper()
        if method == "OPTIONS":
            if cors_origin is None:
                return self._respond(start_response, "403 Forbidden",
                                     b'{"error":"origin_not_allowed"}')
            requested_method = environ.get("HTTP_ACCESS_CONTROL_REQUEST_METHOD", "GET").upper()
            if requested_method != "GET":
                return self._respond(start_response, "405 Method Not Allowed",
                                     b'{"error":"method_not_allowed"}',
                                     origin=cors_origin)
            requested_headers = environ.get("HTTP_ACCESS_CONTROL_REQUEST_HEADERS", "")
            if requested_headers and any(
                header.strip().lower() != "accept"
                for header in requested_headers.split(",")
            ):
                return self._respond(start_response, "400 Bad Request",
                                     b'{"error":"headers_not_allowed"}',
                                     origin=cors_origin)
            return self._respond(start_response, "204 No Content", b"",
                                 origin=cors_origin, preflight=True)
        if method != "GET":
            return self._respond(start_response, "405 Method Not Allowed",
                                 b'{"error":"method_not_allowed"}',
                                 origin=cors_origin)
        try:
            allowed = self._authorize(environ)
        except Exception:
            allowed = False
        if not allowed:
            return self._respond(start_response, "401 Unauthorized",
                                 b'{"error":"unauthorized"}', origin=cors_origin)
        try:
            state = self._snapshot_provider()
            if not isinstance(state, OperatorViewState):
                raise TypeError("snapshot provider returned an unsupported state")
            body = state.encode()
        except Exception:
            return self._respond(start_response, "503 Service Unavailable",
                                 b'{"error":"telemetry_unavailable"}', origin=cors_origin)
        return self._respond(start_response, "200 OK", body, origin=cors_origin)
