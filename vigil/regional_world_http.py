"""Authenticated read-only HTTP bridge for VIGIL regional-world snapshots.

Deploy behind a maintained WSGI server and TLS reverse proxy. The caller-supplied
resolver must validate the bearer token and return only ship IDs observable by
that player; return None for an invalid/expired token.
"""
from __future__ import annotations

import json
from typing import Callable, Iterable
from urllib.parse import urlsplit

from vigil.regional_world import RegionalWorld

VisibleShipsResolver = Callable[[str], set[str] | None]


def _valid_https_origin(origin: str) -> bool:
    try:
        parsed = urlsplit(origin)
        return (
            parsed.scheme == "https" and bool(parsed.netloc)
            and not parsed.path and not parsed.query and not parsed.fragment
        )
    except (TypeError, ValueError):
        return False


def create_regional_snapshot_app(
    *,
    world: RegionalWorld,
    allowed_origins: Iterable[str],
    visible_ships_for_token: VisibleShipsResolver,
    world_bounds: tuple[float, float, float, float] | None = None,
):
    """Create a WSGI endpoint returning only a player's authorized observations."""
    origins = frozenset(allowed_origins)
    if not origins or any(not _valid_https_origin(origin) for origin in origins):
        raise ValueError("allowed_origins must contain exact HTTPS origins")

    def app(environ, start_response):
        origin = environ.get("HTTP_ORIGIN")
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO", "")

        status = "200 OK"
        payload: dict
        if path != "/api/regional/snapshot":
            status, payload = "404 Not Found", {"error": "not_found"}
        elif origin not in origins:
            status, payload = "403 Forbidden", {"error": "origin_not_allowed"}
        elif method == "OPTIONS":
            body = b"{}"
            start_response("204 No Content", [
                ("Content-Length", "0"),
                ("Cache-Control", "no-store"),
                ("Access-Control-Allow-Origin", origin),
                ("Access-Control-Allow-Methods", "GET, OPTIONS"),
                ("Access-Control-Allow-Headers", "Authorization"),
                ("Access-Control-Max-Age", "600"),
                ("Vary", "Origin"),
            ])
            return [b""]
        elif method != "GET":
            status, payload = "405 Method Not Allowed", {"error": "method_not_allowed"}
        else:
            auth = environ.get("HTTP_AUTHORIZATION", "")
            scheme, sep, token = auth.partition(" ")
            if scheme.lower() != "bearer" or not sep or not token.strip():
                status, payload = "401 Unauthorized", {"error": "unauthorized"}
            else:
                try:
                    visible = visible_ships_for_token(token.strip())
                except Exception:
                    visible = None
                if visible is None:
                    status, payload = "401 Unauthorized", {"error": "unauthorized"}
                else:
                    try:
                        payload = world.public_snapshot(set(visible), world_bounds=world_bounds)
                    except (TypeError, ValueError):
                        status, payload = "500 Internal Server Error", {"error": "snapshot_unavailable"}

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
        start_response(status, headers)
        return [body]

    return app
