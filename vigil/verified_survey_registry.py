"""Persistent server-owned evidence registry for artifact-site survey verification.

Only trusted simulation code should call record_confirmed_survey, and only after
it has validated the sensor event and associated it with an authoritative unit.
The public seafloor-survey HTTP endpoint must never write to this registry.
"""
from __future__ import annotations

import json
import re
import sqlite3
import threading
from pathlib import Path
from typing import Any


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
