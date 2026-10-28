"""Persistent registry of confirmed submersible sinking events.

Only trusted simulation code should record events here. Browser-submitted sinking
claims are not authoritative and must never be passed to record_from_simulation.
"""
from __future__ import annotations

import math
import sqlite3
import threading
from pathlib import Path
from typing import Any


def _text(value: Any, field: str, limit: int = 160) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit:
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _coordinates(value: Any) -> tuple[float, float]:
    if not isinstance(value, dict):
        raise ValueError("authoritative sinking coordinates are required")
    x, y = value.get("x"), value.get("y")
    if isinstance(x, bool) or isinstance(y, bool):
        raise ValueError("sinking coordinates must be numeric")
    try:
        x, y = float(x), float(y)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("sinking coordinates must be numeric") from exc
    if not math.isfinite(x) or not math.isfinite(y) or not 0 <= x <= 1 or not 0 <= y <= 1:
        raise ValueError("sinking coordinates must be normalized finite values from 0 to 1")
    return x, y


class SinkingEventRegistry:
    """SQLite-backed lookup for trusted, confirmed sink positions."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self._path = str(path)
        if self._path != ":memory:":
            Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._db = sqlite3.connect(self._path, check_same_thread=False, isolation_level=None, timeout=10)
        self._db.row_factory = sqlite3.Row
        with self._lock:
            if self._path != ":memory:":
                self._db.execute("PRAGMA journal_mode=WAL")
            self._db.execute("""
                CREATE TABLE IF NOT EXISTS confirmed_sinking_events (
                    world_seed TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    crew_id TEXT NOT NULL,
                    unit_id TEXT NOT NULL,
                    x REAL NOT NULL,
                    y REAL NOT NULL,
                    PRIMARY KEY(world_seed, event_id)
                )
            """)

    def close(self) -> None:
        with self._lock:
            self._db.close()

    def record_from_simulation(self, world_seed: str, event: Any, unit_state: Any) -> dict[str, Any]:
        """Record only a confirmed sink event corroborated by authoritative unit state."""
        seed = _text(world_seed, "world_seed", 100)
        if not isinstance(event, dict) or event.get("status") != "CONFIRMED" or event.get("kind") != "UNIT_SUNK":
            raise ValueError("a confirmed UNIT_SUNK simulation event is required")
        event_id = _text(event.get("event_id"), "event_id")
        unit_id = _text(event.get("unit_id"), "unit_id", 120)
        if not isinstance(unit_state, dict) or str(unit_state.get("id", "")) != unit_id:
            raise ValueError("sinking event must match an authoritative unit")
        if unit_state.get("unitType") != "submersible" or unit_state.get("afloat") is not False:
            raise ValueError("sinking event requires a confirmed sunk submersible")
        crew_id = _text(unit_state.get("crewId"), "crew_id", 120)
        x, y = _coordinates({"x": event.get("x"), "y": event.get("y")})
        ux, uy = _coordinates(unit_state)
        if (x, y) != (ux, uy):
            raise ValueError("sinking event coordinates must match the authoritative unit at sinking")
        record = {"world_seed": seed, "event_id": event_id, "crew_id": crew_id,
                  "unit_id": unit_id, "x": x, "y": y}
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                existing = self._db.execute(
                    "SELECT * FROM confirmed_sinking_events WHERE world_seed=? AND event_id=?",
                    (seed, event_id),
                ).fetchone()
                if existing is not None:
                    prior = dict(existing)
                    if prior != record:
                        raise ValueError("sinking event ID was reused with conflicting evidence")
                    self._db.execute("COMMIT")
                    return record
                self._db.execute(
                    "INSERT INTO confirmed_sinking_events(world_seed,event_id,crew_id,unit_id,x,y) VALUES(?,?,?,?,?,?)",
                    (seed, event_id, crew_id, unit_id, x, y),
                )
                self._db.execute("COMMIT")
                return record
            except Exception:
                self._db.execute("ROLLBACK")
                raise

    def resolve_sinking_event(self, crew_id: str, world_seed: str, unit_id: str, event_id: str) -> dict[str, Any] | None:
        """Resolve only a sink event owned by the authenticated crew and named unit."""
        crew = _text(crew_id, "crew_id", 120)
        seed = _text(world_seed, "world_seed", 100)
        uid = _text(unit_id, "unit_id", 120)
        eid = _text(event_id, "event_id")
        with self._lock:
            row = self._db.execute(
                """SELECT x,y FROM confirmed_sinking_events
                   WHERE crew_id=? AND world_seed=? AND unit_id=? AND event_id=?""",
                (crew, seed, uid, eid),
            ).fetchone()
        if row is None:
            return None
        return {"x": row["x"], "y": row["y"]}

