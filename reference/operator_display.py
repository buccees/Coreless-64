"""Versioned, transport-neutral state contract for the remote VIGIL operator display.

This module validates data before a future HTTP/WebSocket adapter serializes it.
It deliberately does not read hardware, infer sensor validity, authenticate users,
or authorize commands; those responsibilities stay in the Coreless runtime and
the server-side session/policy boundary.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any


PROTOCOL_VERSION = 1
CONNECTION_STATES = frozenset({"connected", "stale", "disconnected", "degraded"})
RUNTIME_STATES = frozenset({"ready", "starting", "degraded", "stopped", "faulted"})
SENSOR_STATES = frozenset({"ready", "stale", "disconnected", "degraded", "unavailable"})


def _non_empty_text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _timestamp(value: int, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer timestamp")
    return value


@dataclass(frozen=True)
class OperatorSensorStatus:
    """Health summary for one declared sensor/source, not a sensor driver."""

    sensor_id: str
    modality: str
    state: str
    source_timestamp_ns: int | None = None
    calibration: str = "unspecified"
    reason: str = ""

    def __post_init__(self) -> None:
        _non_empty_text(self.sensor_id, "sensor_id")
        _non_empty_text(self.modality, "modality")
        if self.state not in SENSOR_STATES:
            raise ValueError("unsupported sensor state")
        if self.source_timestamp_ns is not None:
            _timestamp(self.source_timestamp_ns, "source_timestamp_ns")
        _non_empty_text(self.calibration, "calibration")
        if not isinstance(self.reason, str):
            raise ValueError("reason must be text")

    def as_dict(self) -> dict[str, Any]:
        return {
            "sensor_id": self.sensor_id,
            "modality": self.modality,
            "state": self.state,
            "source_timestamp_ns": str(self.source_timestamp_ns) if self.source_timestamp_ns is not None else None,
            "calibration": self.calibration,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class OperatorAlert:
    """A displayable runtime alert with explicit severity and provenance."""

    alert_id: str
    severity: str
    message: str
    source: str
    source_timestamp_ns: int

    def __post_init__(self) -> None:
        for field in ("alert_id", "message", "source"):
            _non_empty_text(getattr(self, field), field)
        if self.severity not in {"info", "warning", "critical"}:
            raise ValueError("unsupported alert severity")
        _timestamp(self.source_timestamp_ns, "source_timestamp_ns")

    def as_dict(self) -> dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "severity": self.severity,
            "message": self.message,
            "source": self.source,
            "source_timestamp_ns": str(self.source_timestamp_ns),
        }


@dataclass(frozen=True)
class OperatorViewState:
    """One immutable, versioned snapshot for a remote browser client."""

    sequence: int
    generated_at_ns: int
    source_timestamp_ns: int
    connection_state: str
    runtime_state: str
    sensors: tuple[OperatorSensorStatus, ...] = ()
    alerts: tuple[OperatorAlert, ...] = ()
    protocol_version: int = PROTOCOL_VERSION

    def __post_init__(self) -> None:
        if self.protocol_version != PROTOCOL_VERSION:
            raise ValueError("unsupported operator display protocol version")
        if isinstance(self.sequence, bool) or not isinstance(self.sequence, int) or self.sequence < 0:
            raise ValueError("sequence must be a non-negative integer")
        _timestamp(self.generated_at_ns, "generated_at_ns")
        _timestamp(self.source_timestamp_ns, "source_timestamp_ns")
        if self.connection_state not in CONNECTION_STATES:
            raise ValueError("unsupported operator connection state")
        if self.runtime_state not in RUNTIME_STATES:
            raise ValueError("unsupported Coreless runtime state")
        if len({sensor.sensor_id for sensor in self.sensors}) != len(self.sensors):
            raise ValueError("sensor IDs must be unique within a view state")
        if len({alert.alert_id for alert in self.alerts}) != len(self.alerts):
            raise ValueError("alert IDs must be unique within a view state")

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-safe protocol object; timestamps are decimal strings.

Nanosecond Unix timestamps exceed JavaScript safe-integer precision, so the
wire representation uses decimal strings to preserve exact source times.
No hidden runtime objects escape.
"""
        return {
            "protocol_version": self.protocol_version,
            "sequence": self.sequence,
            "generated_at_ns": str(self.generated_at_ns),
            "source_timestamp_ns": str(self.source_timestamp_ns),
            "connection_state": self.connection_state,
            "runtime_state": self.runtime_state,
            "sensors": [sensor.as_dict() for sensor in self.sensors],
            "alerts": [alert.as_dict() for alert in self.alerts],
        }

    def encode(self) -> bytes:
        """Serialize deterministically for transport and fixture-based tests."""
        return json.dumps(
            self.as_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
