"""Minimal read-only WSGI endpoint for the remote operator display.

The hosting application must supply authentication/authorization and a live
CorelessSystem instance. This adapter exposes one GET-only JSON snapshot; it
never accepts commands and never invents sensor telemetry.
"""
from __future__ import annotations

import time
from threading import Lock
from typing import Callable, Iterable, Mapping, Any

from operator_display import OperatorViewState

START_RESPONSE = Callable[[str, list[tuple[str, str]]], Any]
Environ = Mapping[str, Any]
Authorizer = Callable[[Environ], bool]
SnapshotProvider = Callable[[], OperatorViewState]


def coreless_view_state(system: Any, *, sequence: int = 0) -> OperatorViewState:
    """Build a truthful base snapshot from an existing CorelessSystem.

    The current reference runtime exposes lifecycle status, not physical sensor
    feeds. Consequently this function intentionally reports no sensors/alerts;
    hardware adapters can be added only when they provide real source metadata.
    """
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
    """Thread-safe snapshot provider bound to one existing CorelessSystem.

    Sequence numbers increase per snapshot request. The provider intentionally
    reports lifecycle only; sensor/alert entries require explicit real adapters.
    """

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
) -> "OperatorTelemetryApp":
    """Create the endpoint adapter for an existing CorelessSystem.

    The caller still mounts the WSGI app behind its production server and
    injects its authenticated session/authorization policy.
    """
    provider = CorelessOperatorSnapshotProvider(system)
    return OperatorTelemetryApp(provider, authorize=authorize, path=path)


class OperatorTelemetryApp:
    """WSGI app exposing an authenticated, read-only operator state endpoint.

    The authorize callback must validate the authenticated server-side session.
    It is deliberately mandatory: no permissive default or browser-side secret.
    """

    def __init__(
        self,
        snapshot_provider: SnapshotProvider,
        *,
        authorize: Authorizer,
        path: str = "/api/operator/state",
    ) -> None:
        if not callable(snapshot_provider):
            raise TypeError("snapshot_provider must be callable")
        if not callable(authorize):
            raise TypeError("authorize callback is required")
        if not path.startswith("/") or path == "/":
            raise ValueError("path must be a non-root absolute path")
        self._snapshot_provider = snapshot_provider
        self._authorize = authorize
        self.path = path

    @staticmethod
    def _respond(start_response: START_RESPONSE, status: str, body: bytes):
        start_response(status, [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(body))),
            ("Cache-Control", "no-store"),
            ("X-Content-Type-Options", "nosniff"),
            ("Vary", "Cookie, Authorization"),
        ])
        return [body]

    def __call__(self, environ: Environ, start_response: START_RESPONSE) -> Iterable[bytes]:
        if environ.get("PATH_INFO") != self.path:
            return self._respond(start_response, "404 Not Found",
                                 b'{"error":"not_found"}')
        if environ.get("REQUEST_METHOD", "GET").upper() != "GET":
            return self._respond(start_response, "405 Method Not Allowed",
                                 b'{"error":"method_not_allowed"}')
        try:
            allowed = self._authorize(environ)
        except Exception:
            allowed = False
        if not allowed:
            return self._respond(start_response, "401 Unauthorized",
                                 b'{"error":"unauthorized"}')
        try:
            state = self._snapshot_provider()
            if not isinstance(state, OperatorViewState):
                raise TypeError("snapshot provider returned an unsupported state")
            body = state.encode()
        except Exception:
            return self._respond(start_response, "503 Service Unavailable",
                                 b'{"error":"telemetry_unavailable"}')
        return self._respond(start_response, "200 OK", body)
