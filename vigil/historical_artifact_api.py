"""Authenticated HTTP API for the server-authoritative PELAGOS artifact ledger.

Integrate this handler into the campaign server's authenticated request router.
The injected identity and unit resolvers must derive crew/unit ownership from server
session state. This module never trusts a client-supplied unit snapshot.
"""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler
import json
from typing import Any, Callable
from urllib.parse import parse_qs, urlsplit

from .historical_artifact_store import HistoricalArtifactStore

MAX_BODY_BYTES = 16_384


def make_historical_artifact_handler(
    store: HistoricalArtifactStore,
    *,
    authenticate: Callable[[BaseHTTPRequestHandler], str | None],
    resolve_unit: Callable[[str], dict[str, Any] | None],
    authorize_unit_action: Callable[[str, str, str], bool],
    authorize_custody_action: Callable[[str, str, str, str], bool],
    authorize_discovery: Callable[[str, str, str], bool],
    validate_sinking_event: Callable[[str, str, str], dict[str, Any] | None] | None = None,
) -> type[BaseHTTPRequestHandler]:
    """Build a JSON handler for /health and /artifacts endpoints.

    authenticate(request) returns the authenticated crew ID or None.
    resolve_unit(crew_id, unit_id) must return authoritative unit state only when
    that crew is allowed to command the unit.
    authorize_discovery(crew_id, world_seed, artifact_id) validates an authoritative
    in-world discovery/site interaction.
    validate_sinking_event(world_seed, unit_id, event_id) returns server-recorded
    last-known coordinates only for a genuine, unconsumed sinking event.
    """
    if not isinstance(store, HistoricalArtifactStore):
        raise TypeError("store must be a HistoricalArtifactStore")
    if not callable(authenticate) or not callable(resolve_unit) or not callable(authorize_unit_action) or not callable(authorize_custody_action) or not callable(authorize_discovery):
        raise TypeError("authentication, unit resolution, and discovery authorization callbacks are required")

    class HistoricalArtifactHandler(BaseHTTPRequestHandler):
        server_version = "VIGIL-ArtifactAPI/1.0"

        def _json(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            self.wfile.write(body)

        def _identity(self) -> str | None:
            try:
                crew_id = authenticate(self)
            except Exception:
                return None
            return crew_id if isinstance(crew_id, str) and crew_id.strip() else None

        def _body(self) -> dict[str, Any]:
            raw_length = self.headers.get("Content-Length")
            if raw_length is None:
                raise ValueError("Content-Length is required")
            try:
                length = int(raw_length)
            except (TypeError, ValueError, OverflowError) as exc:
                raise ValueError("invalid Content-Length") from exc
            if length < 1 or length > MAX_BODY_BYTES:
                raise ValueError("request body must be between 1 and 16384 bytes")
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ValueError("incomplete request body")
            try:
                value = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError("request body must be valid UTF-8 JSON") from exc
            if not isinstance(value, dict):
                raise ValueError("request body must be a JSON object")
            return value

        def do_GET(self) -> None:
            parsed = urlsplit(self.path)
            if parsed.path == "/health":
                self._json(200, {"status": "ok", "api": "historical_artifact_ledger", "authentication_required_for_data": True})
                return
            if parsed.path != "/artifacts":
                self._json(404, {"error": "not_found"})
                return
            crew_id = self._identity()
            if crew_id is None:
                self._json(401, {"error": "authentication_required"})
                return
            query = parse_qs(parsed.query, strict_parsing=False)
            try:
                seed_values = query.get("world_seed", [])
                if len(seed_values) != 1:
                    raise ValueError("exactly one world_seed is required")
                inventory = store.inventory(seed_values[0])
            except (TypeError, ValueError, OverflowError) as exc:
                self._json(400, {"error": "invalid_request", "detail": str(exc)})
                return
            self._json(200, {"schema": "vigil.historical-artifact-ledger", "version": 1,
                             "world_seed": seed_values[0], "crew_id": crew_id,
                             "count": len(inventory), "artifacts": inventory})

        def do_POST(self) -> None:
            if urlsplit(self.path).path != "/artifacts/action":
                self._json(404, {"error": "not_found"})
                return
            crew_id = self._identity()
            if crew_id is None:
                self._json(401, {"error": "authentication_required"})
                return
            try:
                payload = self._body()
                seed = payload.get("world_seed")
                action = payload.get("action")
                artifact_id = payload.get("artifact_id")
                if not all(isinstance(v, str) and v.strip() for v in (seed, action, artifact_id)):
                    raise ValueError("world_seed, action, and artifact_id are required strings")

                if action == "discover":
                    if authorize_discovery(crew_id, seed, artifact_id) is not True:
                        self._json(403, {"error": "discovery_not_authorized"})
                        return
                    result = store.discover(seed, artifact_id)
                elif action in ("collect", "lose"):
                    unit_id = payload.get("unit_id")
                    if not isinstance(unit_id, str) or not unit_id.strip():
                        raise ValueError("unit_id is required")
                    unit = resolve_unit(crew_id, unit_id)
                    if unit is None:
                        self._json(403, {"error": "unit_not_authorized"})
                        return
                    if action == "collect":
                        result = store.collect(seed, artifact_id, unit_id, unit)
                    else:
                        result = store.lose(seed, artifact_id, unit_id, unit)
                elif action in ("transfer", "capture"):
                    source_id, target_id = payload.get("from_unit_id"), payload.get("to_unit_id")
                    if not isinstance(source_id, str) or not isinstance(target_id, str):
                        raise ValueError("from_unit_id and to_unit_id are required")
                    source = resolve_unit(crew_id, source_id)
                    target = resolve_unit(crew_id, target_id)
                    if source is None or target is None:
                        self._json(403, {"error": "unit_not_authorized"})
                        return
                    result = store.transfer(seed, artifact_id, source_id, target_id, source, target,
                                             capture=(action == "capture"))
                elif action == "drop_on_sinking":
                    unit_id, event_id = payload.get("unit_id"), payload.get("sinking_event_id")
                    if not isinstance(unit_id, str) or not isinstance(event_id, str):
                        raise ValueError("unit_id and sinking_event_id are required")
                    if validate_sinking_event is None:
                        self._json(409, {"error": "sinking_event_validation_unavailable"})
                        return
                    event = validate_sinking_event(seed, unit_id, event_id)
                    if not isinstance(event, dict):
                        self._json(403, {"error": "sinking_event_not_authorized"})
                        return
                    result = store.drop_on_sinking(seed, artifact_id, unit_id,
                                                   last_known_x=event.get("x"), last_known_y=event.get("y"),
                                                   sink_event_authorized=True)
                else:
                    self._json(400, {"error": "unsupported_action"})
                    return
            except (TypeError, ValueError, OverflowError) as exc:
                self._json(409, {"error": "action_rejected", "detail": str(exc)})
                return
            except Exception:
                self._json(500, {"error": "internal_error"})
                return
            self._json(200, {"ok": True, "artifact": result})

        def log_message(self, format: str, *args: object) -> None:
            return

    return HistoricalArtifactHandler
