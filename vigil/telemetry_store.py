"""Safe, local persistence for VIGIL network/CSI telemetry metadata.

This module stores packet *metadata* and CSI motion evidence for diagnostics. It
does not inject packets, alter router traffic, capture payloads, or execute SQL
received over the network. All values are bound parameters.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
import sqlite3
from typing import Iterable


@dataclass(frozen=True)
class TelemetryEvent:
    timestamp_ns: int
    sensor_id: str
    event_kind: str
    protocol: str
    packet_length: int
    channel_mhz: int
    signal_dbm: float | None = None
    motion_evidence: float | None = None
    motion_active: bool | None = None

    def __post_init__(self) -> None:
        for name in ("sensor_id", "event_kind", "protocol"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        if isinstance(self.timestamp_ns, bool) or not isinstance(self.timestamp_ns, int) or self.timestamp_ns < 0:
            raise ValueError("timestamp_ns must be a non-negative integer")
        if isinstance(self.packet_length, bool) or not isinstance(self.packet_length, int) or self.packet_length < 0:
            raise ValueError("packet_length must be a non-negative integer")
        if isinstance(self.channel_mhz, bool) or not isinstance(self.channel_mhz, int) or self.channel_mhz < 0:
            raise ValueError("channel_mhz must be a non-negative integer")
        if self.signal_dbm is not None and not isfinite(self.signal_dbm):
            raise ValueError("signal_dbm must be finite when provided")
        if self.motion_evidence is not None and (
            not isfinite(self.motion_evidence) or not 0 <= self.motion_evidence <= 1
        ):
            raise ValueError("motion_evidence must be finite and in [0, 1]")
        if self.motion_active is not None and not isinstance(self.motion_active, bool):
            raise ValueError("motion_active must be a bool when provided")


class TelemetryStore:
    """SQLite event log for local diagnostics; no raw packet payloads are stored."""

    def __init__(self, database: str = ":memory:") -> None:
        self._connection = sqlite3.connect(database)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS telemetry_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp_ns INTEGER NOT NULL,
                sensor_id TEXT NOT NULL,
                event_kind TEXT NOT NULL,
                protocol TEXT NOT NULL,
                packet_length INTEGER NOT NULL,
                channel_mhz INTEGER NOT NULL,
                signal_dbm REAL,
                motion_evidence REAL,
                motion_active INTEGER
            )
        """)
        self._connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_telemetry_timestamp "
            "ON telemetry_events(timestamp_ns)"
        )
        self._connection.commit()

    def record(self, event: TelemetryEvent) -> int:
        """Persist one validated event with a parameterized INSERT."""
        if not isinstance(event, TelemetryEvent):
            raise TypeError("event must be a TelemetryEvent")
        cursor = self._connection.execute(
            """INSERT INTO telemetry_events
               (timestamp_ns, sensor_id, event_kind, protocol, packet_length,
                channel_mhz, signal_dbm, motion_evidence, motion_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event.timestamp_ns, event.sensor_id, event.event_kind,
                event.protocol, event.packet_length, event.channel_mhz,
                event.signal_dbm, event.motion_evidence,
                None if event.motion_active is None else int(event.motion_active),
            ),
        )
        self._connection.commit()
        return int(cursor.lastrowid)

    def recent(self, *, limit: int = 100, sensor_id: str | None = None) -> tuple[dict, ...]:
        """Return newest metadata rows; query filters are also bound parameters."""
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 10_000:
            raise ValueError("limit must be an integer from 1 to 10000")
        if sensor_id is not None and (not isinstance(sensor_id, str) or not sensor_id.strip()):
            raise ValueError("sensor_id must be non-empty when provided")
        if sensor_id is None:
            rows = self._connection.execute(
                "SELECT * FROM telemetry_events ORDER BY timestamp_ns DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        else:
            rows = self._connection.execute(
                """SELECT * FROM telemetry_events WHERE sensor_id = ?
                   ORDER BY timestamp_ns DESC, id DESC LIMIT ?""",
                (sensor_id, limit),
            ).fetchall()
        return tuple(dict(row) for row in rows)

    def close(self) -> None:
        self._connection.close()
