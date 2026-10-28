"""Server-side persistent store for shared PELAGOS seafloor survey records.

Client reports are treated as observations, never as authoritative terrain edits.
Coverage and discovery IDs are idempotent within a world seed. SQLite transactions
and a uniqueness constraint make retries safe across reconnects and concurrent crews.
"""
from __future__ import annotations

import json
import math
import re
import sqlite3
import threading
from pathlib import Path
from typing import Any

SCHEMA = "vigil.seafloor-survey"
SCHEMA_VERSION = 1
MAX_COVERAGE_PER_REPORT = 100_000
MAX_DISCOVERIES_PER_REPORT = 2_000
MAX_SEED_LENGTH = 100
MAX_ID_LENGTH = 160
MAX_KIND_LENGTH = 80


def _world_seed(value: Any) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > MAX_SEED_LENGTH:
        raise ValueError("world_seed must be a non-empty string of at most 100 characters")
    return value.strip()


def _coverage_key(value: Any) -> str:
    if not isinstance(value, str) or not value or len(value) > 80:
        raise ValueError("coverage entries must be non-empty strings of at most 80 characters")
    if not re.fullmatch(r"[A-Za-z0-9_.:,/-]+", value):
        raise ValueError("coverage entry contains unsupported characters")
    return value


def _discovery(value: Any, seed: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("each discovery must be an object")
    record_id = value.get("id")
    if not isinstance(record_id, str) or not record_id.strip() or len(record_id) > MAX_ID_LENGTH:
        raise ValueError("discovery id is invalid")
    if value.get("seed") != seed:
        raise ValueError("discovery world seed does not match survey world_seed")
    x, y = value.get("x"), value.get("y")
    if isinstance(x, bool) or isinstance(y, bool):
        raise ValueError("discovery coordinates must be numeric")
    try:
        x, y = float(x), float(y)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("discovery coordinates must be numeric") from exc
    if not math.isfinite(x) or not math.isfinite(y) or not 0 <= x <= 1 or not 0 <= y <= 1:
        raise ValueError("discovery coordinates must be finite normalized values from 0 to 1")
    depth = value.get("depthMeters")
    if depth is not None:
        if isinstance(depth, bool):
            raise ValueError("depthMeters must be numeric or null")
        try:
            depth = float(depth)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("depthMeters must be numeric or null") from exc
        if not math.isfinite(depth) or not 0 <= depth <= 12000:
            raise ValueError("depthMeters must be between 0 and 12000")
    kind = value.get("kind", "UNKNOWN")
    if not isinstance(kind, str) or not kind.strip():
        raise ValueError("discovery kind must be a non-empty string")
    discovered_at = value.get("discoveredAt", "")
    if not isinstance(discovered_at, str) or len(discovered_at) > 80:
        raise ValueError("discoveredAt must be a short timestamp string")
    scale = value.get("scale", "")
    if not isinstance(scale, str) or len(scale) > 40:
        raise ValueError("scale must be a string of at most 40 characters")
    # Do not let a client promote a sonar indication to a confirmed world fact.
    return {
        "id": record_id.strip(),
        "kind": kind.strip()[:MAX_KIND_LENGTH],
        "x": x,
        "y": y,
        "scale": scale,
        "seed": seed,
        "status": "SONAR INDICATION",
        "discoveredAt": discovered_at,
        "depthMeters": depth,
    }


class SeafloorCampaignStore:
    """SQLite-backed, seed-isolated campaign survey store."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self._path = str(path)
        if self._path != ":memory:":
            Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._db = sqlite3.connect(self._path, check_same_thread=False, isolation_level=None)
        self._db.row_factory = sqlite3.Row
        with self._lock:
            self._db.execute("PRAGMA foreign_keys = ON")
            if self._path != ":memory:":
                self._db.execute("PRAGMA journal_mode = WAL")
            self._db.executescript("""
                CREATE TABLE IF NOT EXISTS seafloor_coverage (
                    world_seed TEXT NOT NULL,
                    cell_key TEXT NOT NULL,
                    first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (world_seed, cell_key)
                );
                CREATE TABLE IF NOT EXISTS seafloor_discoveries (
                    world_seed TEXT NOT NULL,
                    discovery_id TEXT NOT NULL,
                    record_json TEXT NOT NULL,
                    first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_reported_by TEXT,
                    PRIMARY KEY (world_seed, discovery_id)
                );
                CREATE TABLE IF NOT EXISTS seafloor_reports (
                    world_seed TEXT NOT NULL,
                    report_id TEXT NOT NULL,
                    accepted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    coverage_added INTEGER NOT NULL,
                    discoveries_added INTEGER NOT NULL,
                    PRIMARY KEY (world_seed, report_id)
                );
            """)

    def close(self) -> None:
        with self._lock:
            self._db.close()

    def merge_report(self, payload: Any, *, crew_id: str) -> dict[str, Any]:
        """Validate and idempotently merge a client survey report.

        Reusing report_id is safe: the same report is not applied twice. New
        records are individually unique by (world_seed, discovery_id).
        """
        if not isinstance(payload, dict) or payload.get("schema") != SCHEMA:
            raise ValueError("unsupported seafloor survey schema")
        if payload.get("version") != SCHEMA_VERSION:
            raise ValueError("unsupported seafloor survey version")
        seed = _world_seed(payload.get("world_seed"))
        report_id = payload.get("report_id")
        if not isinstance(report_id, str) or not report_id.strip() or len(report_id) > MAX_ID_LENGTH:
            raise ValueError("report_id is required and must be at most 160 characters")
        if not isinstance(crew_id, str) or not crew_id.strip() or len(crew_id) > 160:
            raise ValueError("authenticated crew identity is required")
        raw_coverage = payload.get("coverage", [])
        raw_discoveries = payload.get("discoveries", [])
        if not isinstance(raw_coverage, list) or len(raw_coverage) > MAX_COVERAGE_PER_REPORT:
            raise ValueError("coverage must be a bounded list")
        if not isinstance(raw_discoveries, list) or len(raw_discoveries) > MAX_DISCOVERIES_PER_REPORT:
            raise ValueError("discoveries must be a bounded list")
        coverage = list(dict.fromkeys(_coverage_key(item) for item in raw_coverage))
        discoveries = [_discovery(item, seed) for item in raw_discoveries]
        if len({item["id"] for item in discoveries}) != len(discoveries):
            raise ValueError("report contains duplicate discovery IDs")
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                existing = self._db.execute(
                    "SELECT coverage_added, discoveries_added FROM seafloor_reports WHERE world_seed=? AND report_id=?",
                    (seed, report_id),
                ).fetchone()
                if existing:
                    self._db.execute("COMMIT")
                    return {"ok": True, "duplicate_report": True, "coverage_added": 0,
                            "discoveries_added": 0, "world_seed": seed}
                before_coverage = self._db.total_changes
                for key in coverage:
                    self._db.execute(
                        "INSERT OR IGNORE INTO seafloor_coverage(world_seed,cell_key) VALUES(?,?)",
                        (seed, key),
                    )
                coverage_added = self._db.total_changes - before_coverage
                discoveries_added = 0
                for item in discoveries:
                    cur = self._db.execute(
                        "INSERT OR IGNORE INTO seafloor_discoveries(world_seed,discovery_id,record_json,last_reported_by) VALUES(?,?,?,?)",
                        (seed, item["id"], json.dumps(item, sort_keys=True, separators=(",", ":"), allow_nan=False), crew_id.strip()),
                    )
                    discoveries_added += cur.rowcount
                self._db.execute(
                    "INSERT INTO seafloor_reports(world_seed,report_id,coverage_added,discoveries_added) VALUES(?,?,?,?)",
                    (seed, report_id, coverage_added, discoveries_added),
                )
                self._db.execute("COMMIT")
            except Exception:
                self._db.execute("ROLLBACK")
                raise
        return {"ok": True, "duplicate_report": False, "coverage_added": coverage_added,
                "discoveries_added": discoveries_added, "world_seed": seed}

    def export_survey(self, world_seed: str) -> dict[str, Any]:
        """Return the campaign's merged survey package for a world seed."""
        seed = _world_seed(world_seed)
        with self._lock:
            coverage_rows = self._db.execute(
                "SELECT cell_key FROM seafloor_coverage WHERE world_seed=? ORDER BY cell_key", (seed,)
            ).fetchall()
            discovery_rows = self._db.execute(
                "SELECT record_json FROM seafloor_discoveries WHERE world_seed=? ORDER BY discovery_id", (seed,)
            ).fetchall()
        return {
            "schema": SCHEMA,
            "version": SCHEMA_VERSION,
            "world_seed": seed,
            "coverage": [row["cell_key"] for row in coverage_rows],
            "discoveries": [json.loads(row["record_json"]) for row in discovery_rows],
        }
