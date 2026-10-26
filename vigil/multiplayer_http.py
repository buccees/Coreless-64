"""Same-origin HTTPS HTTP transport for VIGIL multiplayer rooms.

Deploy behind a TLS reverse proxy and route /api/multiplayer/* here. This module
does not itself terminate TLS or serve the static GitHub Pages website.
"""
from __future__ import annotations

import json
import threading
import time
from collections import defaultdict
from typing import Iterable
from urllib.parse import urlsplit

from vigil.multiplayer import BattleshipRooms, MultiplayerError

MAX_BODY_BYTES = 16 * 1024
RATE_WINDOW_SECONDS = 300
CREATE_LIMIT = 10
JOIN_LIMIT = 20


def _valid_https_origin(origin: str) -> bool:
    try:
        parsed = urlsplit(origin)
        return parsed.scheme == "https" and bool(parsed.netloc) and not parsed.path and not parsed.query and not parsed.fragment
    except (TypeError, ValueError):
        return False


class _RateLimit:
    def __init__(self) -> None:
        self._events: dict[tuple[str, str], list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def allow(self, peer: str, action: str, limit: int) -> bool:
        now = time.monotonic()
        key = (peer, action)
        with self._lock:
            recent = [stamp for stamp in self._events[key] if now - stamp < RATE_WINDOW_SECONDS]
            if len(recent) >= limit:
                self._events[key] = recent
                return False
            recent.append(now)
            self._events[key] = recent
            return True


def create_multiplayer_app(
    *, allowed_origins: Iterable[str], rooms: BattleshipRooms | None = None
):
    """Return a WSGI app for authenticated create/join/state/fire operations."""
    origins = frozenset(allowed_origins)
    if not origins or any(not _valid_https_origin(origin) for origin in origins):
        raise ValueError("allowed_origins must contain exact HTTPS origins")
    game = rooms or BattleshipRooms()
    rate_limit = _RateLimit()

    def response(start_response, status: str, payload: dict, origin: str | None = None, preflight: bool = False):
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers = [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(body))),
            ("Cache-Control", "no-store"),
            ("X-Content-Type-Options", "nosniff"),
            ("Referrer-Policy", "no-referrer"),
            ("Vary", "Origin"),
        ]
        if origin in origins:
            headers.append(("Access-Control-Allow-Origin", origin))
        if preflight:
            headers.extend([
                ("Access-Control-Allow-Methods", "GET, POST, OPTIONS"),
                ("Access-Control-Allow-Headers", "Authorization, Content-Type"),
                ("Access-Control-Max-Age", "600"),
            ])
        start_response(status, headers)
        return [body]

    def read_json(environ):
        try:
            length = int(environ.get("CONTENT_LENGTH") or "0")
            if length < 1 or length > MAX_BODY_BYTES:
                raise ValueError
            value = json.loads(environ["wsgi.input"].read(length).decode("utf-8"))
            if not isinstance(value, dict):
                raise ValueError
            return value
        except (ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError):
            raise MultiplayerError("invalid JSON request body") from None

    def token_from(environ):
        header = environ.get("HTTP_AUTHORIZATION", "")
        scheme, separator, token = header.partition(" ")
        if scheme.lower() != "bearer" or not separator or not token.strip():
            raise MultiplayerError("missing player token")
        return token.strip()

    def app(environ, start_response):
        path = environ.get("PATH_INFO", "")
        method = environ.get("REQUEST_METHOD", "GET").upper()
        origin = environ.get("HTTP_ORIGIN")
        peer = environ.get("REMOTE_ADDR", "unknown")

        if path not in {
            "/api/multiplayer/create", "/api/multiplayer/join",
            "/api/multiplayer/state", "/api/multiplayer/fire",
        }:
            return response(start_response, "404 Not Found", {"error": "not_found"})
        if origin not in origins:
            return response(start_response, "403 Forbidden", {"error": "origin_not_allowed"})
        if method == "OPTIONS":
            return response(start_response, "200 OK", {}, origin, preflight=True)

        try:
            if path == "/api/multiplayer/create":
                if method != "POST":
                    return response(start_response, "405 Method Not Allowed", {"error": "method_not_allowed"})
                if not rate_limit.allow(peer, "create", CREATE_LIMIT):
                    return response(start_response, "429 Too Many Requests", {"error": "rate_limited"})
                payload = read_json(environ)
                return response(start_response, "201 Created", game.create_room(payload.get("fleet")))

            if path == "/api/multiplayer/join":
                if method != "POST":
                    return response(start_response, "405 Method Not Allowed", {"error": "method_not_allowed"})
                if not rate_limit.allow(peer, "join", JOIN_LIMIT):
                    return response(start_response, "429 Too Many Requests", {"error": "rate_limited"})
                payload = read_json(environ)
                return response(start_response, "200 OK", game.join_room(payload.get("room_code", ""), payload.get("fleet")))

            if path == "/api/multiplayer/state":
                if method != "GET":
                    return response(start_response, "405 Method Not Allowed", {"error": "method_not_allowed"})
                return response(start_response, "200 OK", game.view(token_from(environ)))

            if path == "/api/multiplayer/fire":
                if method != "POST":
                    return response(start_response, "405 Method Not Allowed", {"error": "method_not_allowed"})
                payload = read_json(environ)
                row, column = payload.get("row"), payload.get("column")
                if type(row) is not int or type(column) is not int:
                    raise MultiplayerError("row and column must be integers")
                return response(start_response, "200 OK", game.fire(token_from(environ), row, column))

        except MultiplayerError as exc:
            message = str(exc)
            status = "401 Unauthorized" if message == "missing player token" or "session not found" in message else "400 Bad Request"
            return response(start_response, status, {"error": "request_rejected", "detail": message})
        return response(start_response, "404 Not Found", {"error": "not_found"})

    return app
