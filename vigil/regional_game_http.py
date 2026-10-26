"""Authenticated WSGI API for the authoritative VIGIL regional game session."""
from __future__ import annotations

import json
from typing import Iterable
from urllib.parse import urlsplit

from vigil.regional_game import RegionalGame, RegionalGameError

MAX_COMMAND_BODY_BYTES = 16 * 1024


def _valid_https_origin(origin: str) -> bool:
    try:
        parsed = urlsplit(origin)
        return (
            parsed.scheme == "https" and bool(parsed.netloc)
            and not parsed.path and not parsed.query and not parsed.fragment
        )
    except (TypeError, ValueError):
        return False


def create_regional_game_app(*, game: RegionalGame, allowed_origins: Iterable[str]):
    """Create snapshot and validated-command endpoints for an existing game.

    This WSGI app deliberately does not start a tick thread. A host/server process
    should own the fixed-rate simulation loop and call game.advance_tick().
    """
    origins = frozenset(allowed_origins)
    if not origins or any(not _valid_https_origin(origin) for origin in origins):
        raise ValueError("allowed_origins must contain exact HTTPS origins")

    def app(environ, start_response):
        origin = environ.get("HTTP_ORIGIN")
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO", "")
        if path not in {"/api/regional/snapshot", "/api/regional/command"}:
            status, payload = "404 Not Found", {"error": "not_found"}
        elif origin not in origins:
            status, payload = "403 Forbidden", {"error": "origin_not_allowed"}
        elif method == "OPTIONS":
            start_response("204 No Content", [
                ("Content-Length", "0"), ("Cache-Control", "no-store"),
                ("Access-Control-Allow-Origin", origin),
                ("Access-Control-Allow-Methods", "GET, POST, OPTIONS"),
                ("Access-Control-Allow-Headers", "Authorization, Content-Type"),
                ("Access-Control-Max-Age", "600"), ("Vary", "Origin"),
            ])
            return [b""]
        elif path.endswith("/snapshot") and method != "GET":
            status, payload = "405 Method Not Allowed", {"error": "method_not_allowed"}
        elif path.endswith("/command") and method != "POST":
            status, payload = "405 Method Not Allowed", {"error": "method_not_allowed"}
        else:
            auth = environ.get("HTTP_AUTHORIZATION", "")
            scheme, sep, token = auth.partition(" ")
            if scheme.lower() != "bearer" or not sep or not token.strip():
                status, payload = "401 Unauthorized", {"error": "unauthorized"}
            elif path.endswith("/snapshot"):
                try:
                    payload = game.snapshot(token.strip())
                    status = "200 OK"
                except RegionalGameError:
                    status, payload = "401 Unauthorized", {"error": "unauthorized"}
                except (TypeError, ValueError):
                    status, payload = "500 Internal Server Error", {"error": "snapshot_unavailable"}
            else:
                try:
                    raw_length = environ.get("CONTENT_LENGTH", "")
                    if not raw_length or not raw_length.isdigit():
                        raise ValueError("invalid_content_length")
                    length = int(raw_length)
                    if length > MAX_COMMAND_BODY_BYTES:
                        status, payload = "413 Payload Too Large", {"error": "payload_too_large"}
                    else:
                        stream = environ["wsgi.input"]
                        raw = stream.read(length)
                        if len(raw) != length:
                            raise ValueError("invalid_body_length")
                        request = json.loads(raw.decode("utf-8"))
                        if not isinstance(request, dict):
                            raise ValueError("invalid_command")
                        operation = request.get("operation")
                        arguments = request.get("arguments", {})
                        if not isinstance(operation, str) or not operation:
                            raise ValueError("invalid_command")
                        result = game.command(token.strip(), operation, arguments)
                        status, payload = "200 OK", result
                except RegionalGameError as exc:
                    message = str(exc)
                    status = "401 Unauthorized" if message == "unauthorized" else "400 Bad Request"
                    payload = {"error": "unauthorized" if status.startswith("401") else "invalid_command",
                               "message": message}
                except (UnicodeDecodeError, json.JSONDecodeError, KeyError, ValueError, TypeError):
                    status, payload = "400 Bad Request", {"error": "invalid_json_or_command"}

        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers = [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(body))), ("Cache-Control", "no-store"),
            ("X-Content-Type-Options", "nosniff"), ("Referrer-Policy", "no-referrer"),
            ("Vary", "Origin"),
        ]
        if origin in origins:
            headers.append(("Access-Control-Allow-Origin", origin))
        start_response(status, headers)
        return [body]

    return app
