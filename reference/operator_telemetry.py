"""Minimal read-only WSGI endpoint for the remote operator display.

The hosting application must supply authentication/authorization and a live
CorelessSystem instance. This adapter exposes one GET-only JSON snapshot; it
never accepts commands and never invents sensor telemetry.
"""
from __future__ import annotations

import time
from threading import Lock
from typing import Callable, Iterable, Mapping, Any, Sequence

from operator_display import OperatorViewState

START_RESPONSE = Callable[[str, list[tuple[str, str]]], Any]
Environ = Mapping[str, Any]
Authorizer = Callable[[Environ], bool]
SnapshotProvider = Callable[[], OperatorViewState]


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
        if any(not isinstance(origin, str) or not origin.startswith("https://")
               for origin in origins):
            raise ValueError("allowed_origins must contain HTTPS origins only")
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
