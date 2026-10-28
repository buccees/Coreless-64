"""Persistent server-owned evidence registry for artifact-site survey verification.

Only trusted simulation code should call record_confirmed_survey, and only after
it has validated the sensor event and associated it with an authoritative unit.
The public seafloor-survey HTTP endpoint must never write to this registry.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

from .historical_artifact_catalog import build_artifact_catalog
from .historical_artifact_store import MAX_RANGE


MAX_ID_LENGTH = 160
MAX_SEED_LENGTH = 100


def _text(value: Any, field: str, limit: int = MAX_ID_LENGTH) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit:
        raise ValueError(f"{field} must be a non-empty string of at most {limit} characters")
    return value.strip()


class VerifiedSurveyRegistry:
    """SQLite-backed registry of simulation-verified artifact-site survey events.

    This class records a trust decision made by its caller; it does not itself
    infer detections from raw sensor samples. The caller must be internal trusted
    simulation code, never an HTTP request handler for client-submitted reports.
    """

    def __init__(self, path: str | Path = ":memory:") -> None:
        self._path = str(path)
        if self._path != ":memory:":
            Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._db = sqlite3.connect(
            self._path, check_same_thread=False, isolation_level=None, timeout=10
        )
        self._db.row_factory = sqlite3.Row
        with self._lock:
            if self._path != ":memory:":
                self._db.execute("PRAGMA journal_mode=WAL")
            self._db.executescript("""
                CREATE TABLE IF NOT EXISTS verified_artifact_surveys (
                    crew_id TEXT NOT NULL,
                    world_seed TEXT NOT NULL,
                    artifact_id TEXT NOT NULL,
                    survey_id TEXT NOT NULL,
                    site_id TEXT NOT NULL,
                    unit_id TEXT NOT NULL,
                    sensor_status TEXT NOT NULL CHECK(sensor_status='accepted'),
                    status TEXT NOT NULL CHECK(status='CONFIRMED'),
                    evidence_json TEXT NOT NULL,
                    recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY(world_seed, artifact_id, survey_id)
                );
                CREATE INDEX IF NOT EXISTS verified_artifact_surveys_lookup
                    ON verified_artifact_surveys(crew_id, world_seed, artifact_id, recorded_at);
            """)

    def close(self) -> None:
        with self._lock:
            self._db.close()

    def record_from_simulation(
        self,
        *,
        crew_id: str,
        world_seed: str,
        artifact_id: str,
        survey_event: dict[str, Any],
        unit_state: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate a trusted simulation event against authoritative unit state.

        Call only from internal simulation code after it has independently
        validated the sensor observation. HTTP/client report handlers must not
        call this method with request payloads.
        """
        crew = _text(crew_id, "crew_id")
        seed = _text(world_seed, "world_seed", MAX_SEED_LENGTH)
        artifact = _text(artifact_id, "artifact_id")
        if not isinstance(survey_event, dict) or not isinstance(unit_state, dict):
            raise ValueError("survey_event and unit_state must be objects")
        catalog = {item["id"]: item for item in build_artifact_catalog()}
        target = catalog.get(artifact)
        if target is None:
            raise ValueError("artifact is not in the canonical catalog")
        if survey_event.get("world_seed") != seed or survey_event.get("artifact_id") != artifact:
            raise ValueError("survey event world or artifact does not match request context")
        if survey_event.get("site_id") != target["siteId"]:
            raise ValueError("survey event does not match the canonical artifact site")
        if survey_event.get("status") != "CONFIRMED" or survey_event.get("sensor_status") != "accepted":
            raise ValueError("survey event must be confirmed and sensor-accepted")
        survey_id = _text(survey_event.get("survey_id"), "survey_id")
        unit_id = _text(survey_event.get("unit_id"), "survey unit_id")
        if unit_state.get("id") != unit_id:
            raise ValueError("survey unit does not match authoritative unit state")
        if unit_state.get("crewId") != crew or unit_state.get("unitType") != "submersible":
            raise ValueError("survey unit must be a submersible owned by this crew")
        if unit_state.get("afloat") is False:
            raise ValueError("survey unit is not afloat")
        x, y = unit_state.get("x"), unit_state.get("y")
        if isinstance(x, bool) or isinstance(y, bool):
            raise ValueError("unit coordinates must be finite numbers")
        try:
            x, y = float(x), float(y)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("unit coordinates must be finite numbers") from exc
        import math
        if not math.isfinite(x) or not math.isfinite(y) or not (0 <= x <= 1 and 0 <= y <= 1):
            raise ValueError("unit coordinates must be within normalized world bounds")
        if math.hypot(x - target["x"], y - target["y"]) > MAX_RANGE:
            raise ValueError("survey unit is outside the artifact-site verification range")
        return self.record_confirmed_survey(
            crew_id=crew,
            world_seed=seed,
            artifact_id=artifact,
            site_id=target["siteId"],
            survey_id=survey_id,
            unit_id=unit_id,
            sensor_status="accepted",
            status="CONFIRMED",
            evidence={"unit_x": x, "unit_y": y},
        )

    def record_confirmed_survey(
        self,
        *,
        crew_id: str,
        world_seed: str,
        artifact_id: str,
        site_id: str,
        survey_id: str,
        unit_id: str,
        sensor_status: str,
        status: str,
        evidence: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Persist a confirmation after trusted simulation validation.

        Reusing a survey ID for the same world/artifact is rejected unless the
        stored evidence is byte-for-byte equivalent after canonical JSON encoding.
        """
        crew = _text(crew_id, "crew_id")
        seed = _text(world_seed, "world_seed", MAX_SEED_LENGTH)
        artifact = _text(artifact_id, "artifact_id")
        site = _text(site_id, "site_id")
        survey = _text(survey_id, "survey_id")
        unit = _text(unit_id, "unit_id")
        if sensor_status != "accepted" or status != "CONFIRMED":
            raise ValueError("only accepted sensor evidence with CONFIRMED status may be recorded")
        if evidence is not None and not isinstance(evidence, dict):
            raise ValueError("evidence must be an object when provided")
        record = {
            "crew_id": crew,
            "world_seed": seed,
            "artifact_id": artifact,
            "site_id": site,
            "survey_id": survey,
            "unit_id": unit,
            "sensor_status": "accepted",
            "status": "CONFIRMED",
        }
        if evidence:
            # Avoid allowing optional fields to override authoritative identity/status.
            for key, value in evidence.items():
                if key not in record:
                    record[key] = value
        encoded = json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False)
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                existing = self._db.execute(
                    """SELECT evidence_json FROM verified_artifact_surveys
                       WHERE world_seed=? AND artifact_id=? AND survey_id=?""",
                    (seed, artifact, survey),
                ).fetchone()
                if existing:
                    if existing["evidence_json"] != encoded:
                        raise ValueError("survey ID already exists with different evidence")
                    self._db.execute("COMMIT")
                    return record
                self._db.execute(
                    """INSERT INTO verified_artifact_surveys
                       (crew_id,world_seed,artifact_id,survey_id,site_id,unit_id,
                        sensor_status,status,evidence_json)
                       VALUES(?,?,?,?,?,?,?,?,?)""",
                    (crew, seed, artifact, survey, site, unit, "accepted", "CONFIRMED", encoded),
                )
                self._db.execute("COMMIT")
                return record
            except Exception:
                self._db.execute("ROLLBACK")
                raise

    def resolve_verified_survey(
        self, crew_id: str, world_seed: str, artifact_id: str
    ) -> dict[str, Any] | None:
        """Resolve the newest trusted confirmation for this crew/world/artifact."""
        crew = _text(crew_id, "crew_id")
        seed = _text(world_seed, "world_seed", MAX_SEED_LENGTH)
        artifact = _text(artifact_id, "artifact_id")
        with self._lock:
            row = self._db.execute(
                """SELECT evidence_json FROM verified_artifact_surveys
                   WHERE crew_id=? AND world_seed=? AND artifact_id=?
                   ORDER BY recorded_at DESC, rowid DESC LIMIT 1""",
                (crew, seed, artifact),
            ).fetchone()
        if row is None:
            return None
        record = json.loads(row["evidence_json"])
        # Resolver contract consumed by make_artifact_discovery_authorizer.
        return {
            "crew_id": record["crew_id"],
            "world_seed": record["world_seed"],
            "artifact_id": record["artifact_id"],
            "site_id": record["site_id"],
            "survey_id": record["survey_id"],
            "unit_id": record["unit_id"],
            "sensor_status": record["sensor_status"],
            "status": record["status"],
        }
