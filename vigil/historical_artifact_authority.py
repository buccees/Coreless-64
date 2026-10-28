"""Authorize unique artifact discovery from trusted simulation survey evidence.

The resolver callbacks must read server-owned simulation state. Client-submitted
seafloor campaign reports are intentionally not accepted as discovery proof.
"""
from __future__ import annotations

import math
from typing import Any, Callable

from .historical_artifact_catalog import build_artifact_catalog
from .historical_artifact_store import MAX_RANGE


def make_artifact_discovery_authorizer(
    *,
    resolve_unit: Callable[[str], dict[str, Any] | None] | None,
    resolve_verified_survey: Callable[[str, str, str], dict[str, Any] | None] | None,
) -> Callable[[str, str, str], bool]:
    """Build a fail-closed verifier backed by authoritative simulation callbacks.

    resolve_verified_survey(crew_id, world_seed, artifact_id) must return a
    server-generated record with: unit_id, world_seed, artifact_id, site_id,
    survey_id, status='CONFIRMED', sensor_status='accepted'. The returned unit
    must be server-resolved, active, owned by crew_id, and near the canonical
    artifact site. Do not implement the resolver using browser POST payloads or
    the shared client-report store.
    """
    catalog = {item["id"]: item for item in build_artifact_catalog()}

    def authorize(crew_id: str, world_seed: str, artifact_id: str) -> bool:
        if not all(isinstance(value, str) and value.strip()
                   for value in (crew_id, world_seed, artifact_id)):
            return False
        if not callable(resolve_unit) or not callable(resolve_verified_survey):
            return False
        artifact = catalog.get(artifact_id)
        if artifact is None:
            return False
        try:
            evidence = resolve_verified_survey(crew_id, world_seed, artifact_id)
            if not isinstance(evidence, dict):
                return False
            if (evidence.get("world_seed") != world_seed
                    or evidence.get("artifact_id") != artifact_id
                    or evidence.get("site_id") != artifact["siteId"]
                    or evidence.get("status") != "CONFIRMED"
                    or evidence.get("sensor_status") != "accepted"):
                return False
            survey_id = evidence.get("survey_id")
            unit_id = evidence.get("unit_id")
            if not isinstance(survey_id, str) or not survey_id.strip():
                return False
            if not isinstance(unit_id, str) or not unit_id.strip():
                return False
            unit = resolve_unit(unit_id)
            if not isinstance(unit, dict) or unit.get("id") != unit_id:
                return False
            if unit.get("crewId") != crew_id or unit.get("unitType") != "submersible" or unit.get("afloat") is False:
                return False
            if evidence.get("unit_id") != unit.get("id"):
                return False
            x, y = unit.get("x"), unit.get("y")
            if isinstance(x, bool) or isinstance(y, bool):
                return False
            x, y = float(x), float(y)
            if not math.isfinite(x) or not math.isfinite(y) or not (0 <= x <= 1 and 0 <= y <= 1):
                return False
            return math.hypot(x - artifact["x"], y - artifact["y"]) <= MAX_RANGE
        except (KeyError, TypeError, ValueError, OverflowError):
            return False

    return authorize
