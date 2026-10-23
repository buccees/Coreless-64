"""Authenticated HTTPS LAN host for the read-only Coreless operator display.

Run from the repository root with a TLS certificate/key and a strong password
in CORELESS_OPERATOR_PASSWORD. Sessions are in-memory and expire on restart.
This is a small LAN deployment, not a substitute for a hardened public server.
"""
from __future__ import annotations

import argparse
import hmac
import json
import os
import secrets
import sys
import threading
import time
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Any
from wsgiref.simple_server import WSGIServer, WSGIRequestHandler, make_server
import ssl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "reference"))

from operator_telemetry import CorelessSessionAuthorizer, create_coreless_operator_app
from operator_display import OperatorViewState
from system import CorelessSystem
from vigil.security import AuthorizationContext
from vigil.spatial_snapshot import build_spatial_snapshot
from vigil.spatial_registry_store import SpatialRegistryStore
from vigil.workspace import SpatialWorkspace

SESSION_COOKIE = "coreless_operator_session"
SESSION_TTL_SECONDS = 30 * 60
MAX_LOGIN_ATTEMPTS = 8
LOGIN_WINDOW_SECONDS = 5 * 60


class LocalSessions:
    """In-memory opaque sessions with expiry, revocation, and simple throttling."""

    def __init__(self, *, ttl_seconds: int = SESSION_TTL_SECONDS) -> None:
        self._ttl = ttl_seconds
        self._sessions: dict[str, tuple[float, AuthorizationContext]] = {}
        self._attempts: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def _prune(self, now: float) -> None:
        self._sessions = {k: v for k, v in self._sessions.items() if v[0] > now}
        self._attempts = {
            k: [t for t in times if now - t < LOGIN_WINDOW_SECONDS]
            for k, times in self._attempts.items()
            if any(now - t < LOGIN_WINDOW_SECONDS for t in times)
        }

    def can_attempt(self, peer: str) -> bool:
        now = time.monotonic()
        with self._lock:
            self._prune(now)
            return len(self._attempts.get(peer, [])) < MAX_LOGIN_ATTEMPTS

    def record_attempt(self, peer: str) -> None:
        now = time.monotonic()
        with self._lock:
            self._prune(now)
            self._attempts.setdefault(peer, []).append(now)

    def create(self) -> tuple[str, AuthorizationContext]:
        token = secrets.token_urlsafe(32)
        context = AuthorizationContext(
            session_id=secrets.token_urlsafe(18),
            scopes=frozenset({"operator:read"}),
        )
        with self._lock:
            self._sessions[token] = (time.monotonic() + self._ttl, context)
        return token, context

    def resolve(self, token: str | None) -> AuthorizationContext | None:
        if not token:
            return None
        now = time.monotonic()
        with self._lock:
            self._prune(now)
            item = self._sessions.get(token)
            return item[1] if item else None

    def revoke(self, token: str | None) -> None:
        if token:
            with self._lock:
                self._sessions.pop(token, None)


def _json(start_response, status: str, payload: dict[str, Any], headers=None):
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    response_headers = [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(body))),
        ("Cache-Control", "no-store"),
        ("X-Content-Type-Options", "nosniff"),
        ("Referrer-Policy", "no-referrer"),
        ("Content-Security-Policy", "default-src 'self'; connect-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'"),
    ]
    response_headers.extend(headers or [])
    start_response(status, response_headers)
    return [body]


def _cookie_token(environ) -> str | None:
    cookie = SimpleCookie()
    try:
        cookie.load(environ.get("HTTP_COOKIE", ""))
        morsel = cookie.get(SESSION_COOKIE)
        return morsel.value if morsel else None
    except Exception:
        return None


def create_lan_app(
    *, password: str, system: CorelessSystem, page_path: Path | None = None,
    spatial_workspace: SpatialWorkspace | None = None,
):
    if not isinstance(password, str) or len(password) < 16:
        raise ValueError("CORELESS_OPERATOR_PASSWORD must contain at least 16 characters")
    page = page_path or ROOT / "operator-display.html"
    if not page.is_file():
        raise FileNotFoundError(page)

    if not isinstance(system, CorelessSystem):
        raise TypeError("system must be the active CorelessSystem instance")
    if spatial_workspace is not None and not isinstance(spatial_workspace, SpatialWorkspace):
        raise TypeError("spatial_workspace must be a SpatialWorkspace when provided")
    sessions = LocalSessions()
    telemetry = create_coreless_operator_app(
        system,
        authorize=CorelessSessionAuthorizer(),
        allowed_origins=(),
    )
    password_bytes = password.encode("utf-8")

    def app(environ, start_response):
        path = environ.get("PATH_INFO", "/")
        method = environ.get("REQUEST_METHOD", "GET").upper()
        peer = environ.get("REMOTE_ADDR", "unknown")
        token = _cookie_token(environ)
        context = sessions.resolve(token)
        # Never trust browser-supplied identity/scopes; populate only from server session storage.
        environ["coreless.authorization_context"] = context

        if path in ("/", "/operator-display.html") and method == "GET":
            body = page.read_bytes()
            start_response("200 OK", [
                ("Content-Type", "text/html; charset=utf-8"),
                ("Content-Length", str(len(body))),
                ("Cache-Control", "no-store"),
                ("X-Content-Type-Options", "nosniff"),
                ("Referrer-Policy", "no-referrer"),
                ("Content-Security-Policy", "default-src 'self'; connect-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'"),
            ])
            return [body]

        if path == "/api/operator/login":
            if method != "POST":
                return _json(start_response, "405 Method Not Allowed", {"error": "method_not_allowed"}, [("Allow", "POST")])
            origin = environ.get("HTTP_ORIGIN")
            expected_origin = "https://" + environ.get("HTTP_HOST", "")
            if not origin or origin != expected_origin:
                return _json(start_response, "403 Forbidden", {"error": "origin_not_allowed"})
            if not sessions.can_attempt(peer):
                return _json(start_response, "429 Too Many Requests", {"error": "try_later"}, [("Retry-After", "300")])
            try:
                length = int(environ.get("CONTENT_LENGTH") or "0")
                if length < 1 or length > 4096:
                    raise ValueError("invalid body size")
                payload = json.loads(environ["wsgi.input"].read(length).decode("utf-8"))
                supplied = payload.get("password") if isinstance(payload, dict) else None
                if not isinstance(supplied, str):
                    supplied = ""
            except Exception:
                supplied = ""
            sessions.record_attempt(peer)
            if not hmac.compare_digest(supplied.encode("utf-8"), password_bytes):
                return _json(start_response, "401 Unauthorized", {"error": "invalid_credentials"})
            sessions.revoke(token)
            new_token, _ = sessions.create()
            return _json(start_response, "200 OK", {"authenticated": True, "expires_in": SESSION_TTL_SECONDS}, [
                ("Set-Cookie", f"{SESSION_COOKIE}={new_token}; Path=/; Max-Age={SESSION_TTL_SECONDS}; HttpOnly; Secure; SameSite=Strict"),
            ])

        if path == "/api/operator/logout":
            if method != "POST":
                return _json(start_response, "405 Method Not Allowed", {"error": "method_not_allowed"}, [("Allow", "POST")])
            origin = environ.get("HTTP_ORIGIN")
            expected_origin = "https://" + environ.get("HTTP_HOST", "")
            if not origin or origin != expected_origin:
                return _json(start_response, "403 Forbidden", {"error": "origin_not_allowed"})
            sessions.revoke(token)
            return _json(start_response, "200 OK", {"authenticated": False}, [
                ("Set-Cookie", f"{SESSION_COOKIE}=; Path=/; Max-Age=0; HttpOnly; Secure; SameSite=Strict"),
            ])

        if path == "/api/operator/session" and method == "GET":
            return _json(start_response, "200 OK", {
                "authenticated": context is not None,
                "expires_in": SESSION_TTL_SECONDS if context is not None else 0,
            })

        if path == "/api/vigil/alerts/acknowledge":
            if method != "POST":
                return _json(start_response, "405 Method Not Allowed",
                             {"error": "method_not_allowed"}, [("Allow", "POST")])
            if context is None:
                return _json(start_response, "401 Unauthorized", {"error": "unauthorized"})
            origin = environ.get("HTTP_ORIGIN")
            expected_origin = "https://" + environ.get("HTTP_HOST", "")
            if not origin or origin != expected_origin:
                return _json(start_response, "403 Forbidden", {"error": "origin_not_allowed"})
            if spatial_workspace is None or spatial_workspace.registry_store is None:
                return _json(start_response, "503 Service Unavailable", {
                    "error": "persistent_spatial_workspace_required",
                    "detail": "Persistent alert acknowledgements require a configured spatial registry.",
                })
            try:
                length = int(environ.get("CONTENT_LENGTH") or "0")
                if length < 1 or length > 4096:
                    raise ValueError("invalid body size")
                payload = json.loads(environ["wsgi.input"].read(length).decode("utf-8"))
                alert_id = payload.get("alert_id") if isinstance(payload, dict) else None
                acknowledged = payload.get("acknowledged", True) if isinstance(payload, dict) else True
                if not isinstance(alert_id, str) or not alert_id.strip() or not isinstance(acknowledged, bool):
                    raise ValueError("invalid acknowledgement payload")
                current = build_spatial_snapshot(spatial_workspace, now_ns=time.monotonic_ns())
                active_ids = {item["alert_id"] for item in current["sensor_health_alerts"]}
                if alert_id not in active_ids:
                    return _json(start_response, "409 Conflict", {
                        "error": "alert_not_active",
                        "detail": "The alert is no longer active; refresh the spatial snapshot.",
                    })
                spatial_workspace.set_sensor_alert_acknowledgement(
                    alert_id, acknowledged=acknowledged, acknowledged_by="authenticated_operator"
                )
            except ValueError as exc:
                return _json(start_response, "400 Bad Request", {"error": "invalid_payload", "detail": str(exc)})
            except Exception:
                return _json(start_response, "503 Service Unavailable", {
                    "error": "acknowledgement_unavailable",
                    "detail": "The alert acknowledgement could not be saved.",
                })
            return _json(start_response, "200 OK", {
                "alert_id": alert_id, "acknowledged": acknowledged,
            })

        if path == "/api/vigil/spatial":
            if method != "GET":
                return _json(start_response, "405 Method Not Allowed",
                             {"error": "method_not_allowed"}, [("Allow", "GET")])
            if context is None:
                return _json(start_response, "401 Unauthorized", {"error": "unauthorized"})
            if spatial_workspace is None:
                return _json(start_response, "503 Service Unavailable", {
                    "error": "spatial_not_configured",
                    "detail": "No VIGIL spatial workspace was attached to this operator session.",
                })
            try:
                # Spatial observations use monotonic nanoseconds; wall-clock epoch time would
                # make otherwise fresh sensor readings appear ancient or future-dated.
                payload = build_spatial_snapshot(spatial_workspace, now_ns=time.monotonic_ns())
            except Exception:
                # Keep exception internals and local paths out of the authenticated API.
                return _json(start_response, "503 Service Unavailable", {
                    "error": "spatial_snapshot_unavailable",
                    "detail": "The current spatial snapshot could not be assembled.",
                })
            return _json(start_response, "200 OK", payload)

        if path == "/api/operator/state":
            return telemetry(environ, start_response)

        if method != "GET":
            return _json(start_response, "405 Method Not Allowed", {"error": "method_not_allowed"}, [("Allow", "GET")])
        return _json(start_response, "404 Not Found", {"error": "not_found"})

    return app


def serve_lan(
    system: CorelessSystem,
    *,
    host: str,
    port: int,
    cert_path: str | Path,
    key_path: str | Path,
    password: str,
    spatial_workspace: SpatialWorkspace | None = None,
) -> None:
    """Serve the operator display against the caller's already-running machine."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(str(cert_path), str(key_path))
    server = make_server(
        host,
        port,
        create_lan_app(
            password=password, system=system, spatial_workspace=spatial_workspace
        ),
        server_class=WSGIServer,
        handler_class=QuietHandler,
    )
    server.socket = context.wrap_socket(server.socket, server_side=True)
    print(f"Coreless operator display listening at https://{host}:{port}/")
    print("The browser is a remote terminal; this process retains machine ownership.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


class QuietHandler(WSGIRequestHandler):
    def log_message(self, fmt, *args):
        # Avoid logging cookies, request bodies, or other potentially sensitive data.
        print("LAN operator server:", fmt % args)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Coreless operator display with its persistent machine.")
    parser.add_argument("--host", default="127.0.0.1", help="bind address; use 0.0.0.0 to allow LAN clients")
    parser.add_argument("--port", type=int, default=8443)
    parser.add_argument("--image", type=Path, required=True, help="persistent Coreless machine image path; must not be open by another process")
    parser.add_argument("--spatial-db", type=Path, help="persistent VIGIL spatial registry path; defaults beside the machine image")
    parser.add_argument("--blueprint", type=Path, help="optional versioned VIGIL blueprint JSON manifest to import and activate")
    parser.add_argument("--level", help="optional floor/level ID to select for the spatial overlay")
    parser.add_argument("--cert", default=os.environ.get("CORELESS_TLS_CERT"), help="TLS certificate PEM path")
    parser.add_argument("--key", default=os.environ.get("CORELESS_TLS_KEY"), help="TLS private key PEM path")
    args = parser.parse_args()
    password = os.environ.get("CORELESS_OPERATOR_PASSWORD", "")
    if len(password) < 16:
        parser.error("set CORELESS_OPERATOR_PASSWORD to a unique password of at least 16 characters")
    if not args.cert or not args.key:
        parser.error("TLS is required: provide --cert/--key or CORELESS_TLS_CERT/CORELESS_TLS_KEY")
    system = CorelessSystem(storage_path=args.image)
    system.boot()
    spatial_database = args.spatial_db or args.image.with_name(args.image.name + ".vigil-spatial.sqlite3")
    spatial_store = SpatialRegistryStore(str(spatial_database))
    spatial_workspace = SpatialWorkspace(registry_store=spatial_store)
    if args.blueprint:
        spatial_workspace.import_blueprint(args.blueprint.read_bytes(), activate=True)
    active_model = spatial_workspace.active_model
    if args.level:
        spatial_workspace.select_level(args.level)
    elif active_model is not None:
        # Do not silently stack separate floor plans in the same 2-D viewport.
        levels = sorted({feature.level for feature in active_model.features if feature.level})
        if levels:
            spatial_workspace.select_level(levels[0])
    try:
        serve_lan(
            system, host=args.host, port=args.port, cert_path=args.cert, key_path=args.key,
            password=password, spatial_workspace=spatial_workspace,
        )
    finally:
        system.machine.save_state()
        spatial_store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
