"""Authoritative, transactional custody ledger for unique PELAGOS historical artifacts.

This module is a server-side primitive, not a browser-storage adapter. Callers must
supply unit state loaded by the server from the authoritative simulation, never from
untrusted client coordinates. Each world seed has exactly one row per catalog artifact.
"""
from __future__ import annotations

import json
import math
import re
import sqlite3
import threading
from pathlib import Path
from typing import Any, Iterable

SCHEMA = "vigil.historical-artifact-ledger"
SCHEMA_VERSION = 1
MAX_SEED_LENGTH = 100
MAX_ID_LENGTH = 160
MAX_UNIT_ID_LENGTH = 120
MAX_RANGE = 0.035


def _text(value: Any, label: str, limit: int = MAX_ID_LENGTH) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit:
        raise ValueError(f"{label} must be a non-empty string of at most {limit} characters")
    return value.strip()


def _position(unit: dict[str, Any]) -> tuple[float, float]:
    x, y = unit.get("x"), unit.get("y")
    if isinstance(x, bool) or isinstance(y, bool):
        raise ValueError("authoritative unit coordinates must be numeric")
    try:
        x, y = float(x), float(y)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("authoritative unit coordinates must be numeric") from exc
    if not math.isfinite(x) or not math.isfinite(y) or not 0 <= x <= 1 or not 0 <= y <= 1:
        raise ValueError("authoritative unit coordinates must be normalized values from 0 to 1")
    return x, y


def _active_submersible(unit: Any, unit_id: str) -> dict[str, Any]:
    if not isinstance(unit, dict) or str(unit.get("id", "")) != unit_id:
        raise ValueError("unit must be resolved by the authoritative server")
    if unit.get("unitType") != "submersible" or unit.get("afloat") is False:
        raise ValueError("custody actions require an active submersible")
    container = unit.get("lockedArtifactContainer")
    if not isinstance(container, dict) or container.get("locked") is not True:
        raise ValueError("custody actions require a preconfigured locked container")
    _position(unit)
    return unit


class HistoricalArtifactStore:
    """SQLite ledger with transactional uniqueness and server-validated custody."""

    def __init__(self, catalog: Iterable[dict[str, Any]], path: str | Path = ":memory:") -> None:
        self._catalog: dict[str, dict[str, Any]] = {}
        for raw in catalog:
            if not isinstance(raw, dict):
                raise ValueError("each catalog entry must be an object")
            item_id = _text(raw.get("id"), "artifact id")
            if item_id in self._catalog:
                raise ValueError(f"duplicate catalog artifact id: {item_id}")
            site_id = _text(raw.get("siteId"), "artifact site id")
            x, y = _position({"x": raw.get("x"), "y": raw.get("y")})
            self._catalog[item_id] = {"id": item_id, "siteId": site_id, "x": x, "y": y}
        self._path = str(path)
        if self._path != ":memory:":
            Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._db = sqlite3.connect(self._path, check_same_thread=False, isolation_level=None, timeout=10)
        self._db.row_factory = sqlite3.Row
        with self._lock:
            self._db.execute("PRAGMA foreign_keys=ON")
            if self._path != ":memory:":
                self._db.execute("PRAGMA journal_mode=WAL")
            self._db.executescript("""
                CREATE TABLE IF NOT EXISTS historical_artifacts (
                    world_seed TEXT NOT NULL,
                    artifact_id TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('AT_SITE','CARRIED','LOST')),
                    discovered INTEGER NOT NULL DEFAULT 0 CHECK(discovered IN (0,1)),
                    source_site_id TEXT NOT NULL,
                    x REAL NOT NULL,
                    y REAL NOT NULL,
                    carrier_id TEXT NOT NULL DEFAULT '',
                    revision INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY(world_seed, artifact_id)
                );
                CREATE TABLE IF NOT EXISTS historical_artifact_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    world_seed TEXT NOT NULL,
                    artifact_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    actor_unit_id TEXT NOT NULL DEFAULT '',
                    other_unit_id TEXT NOT NULL DEFAULT '',
                    x REAL NOT NULL,
                    y REAL NOT NULL,
                    revision INTEGER NOT NULL,
                    occurred_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(world_seed, artifact_id)
                      REFERENCES historical_artifacts(world_seed, artifact_id)
                );
            """)

    def close(self) -> None:
        with self._lock:
            self._db.close()

    def _seed(self, value: Any) -> str:
        return _text(value, "world_seed", MAX_SEED_LENGTH)

    def _artifact(self, artifact_id: Any) -> dict[str, Any]:
        key = _text(artifact_id, "artifact id")
        if key not in self._catalog:
            raise ValueError("unknown artifact id")
        return self._catalog[key]

    def _ensure(self, seed: str, artifact: dict[str, Any]) -> sqlite3.Row:
        self._db.execute(
            """INSERT OR IGNORE INTO historical_artifacts
               (world_seed,artifact_id,status,discovered,source_site_id,x,y)
               VALUES(?,?,'AT_SITE',0,?,?,?)""",
            (seed, artifact["id"], artifact["siteId"], artifact["x"], artifact["y"]),
        )
        return self._db.execute(
            "SELECT * FROM historical_artifacts WHERE world_seed=? AND artifact_id=?",
            (seed, artifact["id"]),
        ).fetchone()

    @staticmethod
    def _view(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["artifact_id"], "status": row["status"],
            "discovered": bool(row["discovered"]), "sourceSiteId": row["source_site_id"],
            "location": {"x": row["x"], "y": row["y"]},
            "carrierId": row["carrier_id"], "revision": row["revision"],
            "unique": True, "respawnable": False,
        }

    def inventory(self, world_seed: str) -> list[dict[str, Any]]:
        seed = self._seed(world_seed)
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                rows = [self._ensure(seed, item) for item in self._catalog.values()]
                result = [self._view(row) for row in rows]
                self._db.execute("COMMIT")
                return result
            except Exception:
                self._db.execute("ROLLBACK")
                raise

    def discover(self, world_seed: str, artifact_id: str, source_site_id: str | None = None) -> dict[str, Any]:
        seed, item = self._seed(world_seed), self._artifact(artifact_id)
        site = _text(source_site_id or item["siteId"], "source site id")
        if site != item["siteId"]:
            raise ValueError("artifact can only be discovered at its catalogued recovery site")
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                row = self._ensure(seed, item)
                newly_discovered = not bool(row["discovered"])
                if newly_discovered:
                    self._db.execute(
                        """UPDATE historical_artifacts SET discovered=1,revision=revision+1,
                           updated_at=CURRENT_TIMESTAMP WHERE world_seed=? AND artifact_id=?""",
                        (seed, item["id"]),
                    )
                    row = self._db.execute(
                        "SELECT * FROM historical_artifacts WHERE world_seed=? AND artifact_id=?",
                        (seed, item["id"]),
                    ).fetchone()
                    self._event(seed, item["id"], "DISCOVER", "", "", row["x"], row["y"], row["revision"])
                self._db.execute("COMMIT")
                return self._view(row)
            except Exception:
                self._db.execute("ROLLBACK")
                raise

    def _event(self, seed: str, artifact_id: str, action: str, actor: str, other: str,
               x: float, y: float, revision: int) -> None:
        self._db.execute(
            """INSERT INTO historical_artifact_events
               (world_seed,artifact_id,action,actor_unit_id,other_unit_id,x,y,revision)
               VALUES(?,?,?,?,?,?,?,?)""",
            (seed, artifact_id, action, actor, other, x, y, revision),
        )

    def _mutate(self, seed: str, item: dict[str, Any], *, action: str,
                status: str, carrier: str, x: float, y: float,
                actor: str = "", other: str = "") -> dict[str, Any]:
        self._db.execute(
            """UPDATE historical_artifacts SET status=?,carrier_id=?,x=?,y=?,
               revision=revision+1,updated_at=CURRENT_TIMESTAMP
               WHERE world_seed=? AND artifact_id=?""",
            (status, carrier, x, y, seed, item["id"]),
        )
        row = self._db.execute(
            "SELECT * FROM historical_artifacts WHERE world_seed=? AND artifact_id=?",
            (seed, item["id"]),
        ).fetchone()
        self._event(seed, item["id"], action, actor, other, x, y, row["revision"])
        return self._view(row)

    def collect(self, world_seed: str, artifact_id: str, unit_id: str,
                authoritative_unit: dict[str, Any]) -> dict[str, Any]:
        seed, item, uid = self._seed(world_seed), self._artifact(artifact_id), _text(unit_id, "unit id", MAX_UNIT_ID_LENGTH)
        unit = _active_submersible(authoritative_unit, uid)
        x, y = _position(unit)
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                row = self._ensure(seed, item)
                if not row["discovered"]:
                    raise ValueError("artifact must be discovered before collection")
                if row["status"] == "CARRIED":
                    raise ValueError("unique artifact is already in custody")
                if math.hypot(x-row["x"], y-row["y"]) > MAX_RANGE:
                    raise ValueError("submersible must reach the artifact's current coordinates")
                result = self._mutate(seed, item, action="COLLECT", status="CARRIED",
                                      carrier=uid, x=row["x"], y=row["y"], actor=uid)
                self._db.execute("COMMIT")
                return result
            except Exception:
                self._db.execute("ROLLBACK")
                raise

    def lose(self, world_seed: str, artifact_id: str, carrier_id: str,
             authoritative_carrier: dict[str, Any]) -> dict[str, Any]:
        seed, item, uid = self._seed(world_seed), self._artifact(artifact_id), _text(carrier_id, "carrier id", MAX_UNIT_ID_LENGTH)
        unit = _active_submersible(authoritative_carrier, uid)
        x, y = _position(unit)
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                row = self._ensure(seed, item)
                if row["status"] != "CARRIED" or row["carrier_id"] != uid:
                    raise ValueError("this submersible does not hold artifact custody")
                result = self._mutate(seed, item, action="LOSS", status="LOST", carrier="", x=x, y=y, actor=uid)
                self._db.execute("COMMIT")
                return result
            except Exception:
                self._db.execute("ROLLBACK")
                raise

    def transfer(self, world_seed: str, artifact_id: str, from_unit_id: str, to_unit_id: str,
                 authoritative_from: dict[str, Any], authoritative_to: dict[str, Any],
                 *, capture: bool = False) -> dict[str, Any]:
        seed, item = self._seed(world_seed), self._artifact(artifact_id)
        source_id = _text(from_unit_id, "source unit id", MAX_UNIT_ID_LENGTH)
        target_id = _text(to_unit_id, "destination unit id", MAX_UNIT_ID_LENGTH)
        if source_id == target_id:
            raise ValueError("source and destination must be different units")
        source, target = _active_submersible(authoritative_from, source_id), _active_submersible(authoritative_to, target_id)
        sx, sy = _position(source)
        tx, ty = _position(target)
        if math.hypot(sx-tx, sy-ty) > MAX_RANGE:
            raise ValueError("submersibles must be within transfer or boarding range")
        hostile = str(source.get("side", "friendly")) != str(target.get("side", "friendly"))
        if capture and not hostile:
            raise ValueError("custody capture requires opposing factions")
        if not capture and hostile:
            raise ValueError("routine transfer between opposing factions is not permitted")
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                row = self._ensure(seed, item)
                if row["status"] != "CARRIED" or row["carrier_id"] != source_id:
                    raise ValueError("source submersible does not have custody")
                result = self._mutate(seed, item, action="CAPTURE" if capture else "TRANSFER",
                                      status="CARRIED", carrier=target_id, x=row["x"], y=row["y"],
                                      actor=target_id, other=source_id)
                self._db.execute("COMMIT")
                return result
            except Exception:
                self._db.execute("ROLLBACK")
                raise

    def events(self, world_seed: str, artifact_id: str) -> list[dict[str, Any]]:
        seed, item = self._seed(world_seed), self._artifact(artifact_id)
        with self._lock:
            rows = self._db.execute(
                """SELECT action,actor_unit_id,other_unit_id,x,y,revision,occurred_at
                   FROM historical_artifact_events WHERE world_seed=? AND artifact_id=?
                   ORDER BY event_id""", (seed, item["id"]),
            ).fetchall()
        return [{"action": r["action"], "actorUnitId": r["actor_unit_id"],
                 "otherUnitId": r["other_unit_id"], "location": {"x": r["x"], "y": r["y"]},
                 "revision": r["revision"], "occurredAt": r["occurred_at"]} for r in rows]

    def contract(self) -> dict[str, Any]:
        return {"schema": SCHEMA, "version": SCHEMA_VERSION,
                "custodyAuthority": "server", "uniqueKey": ["world_seed", "artifact_id"],
                "operations": ["inventory", "discover", "collect", "lose", "transfer", "capture", "events"],
                "clientCoordinatesTrusted": False, "respawnable": False}
