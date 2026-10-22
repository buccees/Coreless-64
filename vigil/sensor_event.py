"""Validated, display-ready sensor event records for the VIGIL Control Room.

This model normalizes event metadata across sensor families. It does not acquire
hardware data, calculate detections, or turn contextual evidence into positions.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from math import isfinite


class SensorEventStatus(str, Enum):
    ACCEPTED = "accepted"
    CONTEXT = "context"
    REJECTED = "rejected"
    WARNING = "warning"


@dataclass(frozen=True)
class SensorEventRecord:
    """One normalized sensor event suitable for a dashboard or JSON API."""

    event_id: str
    sensor_id: str
    timestamp_ns: int
    modality: str
    event_kind: str
    status: SensorEventStatus
    reason: str
    sequence: int | None = None
    signal_dbm: float | None = None
    confidence: float | None = None
    evidence_score: float | None = None
    uncertainty_m: float | None = None
    calibration_status: str = "unknown"
    model_id: str | None = None
    model_revision: str | None = None
    frame_id: str | None = None

    def __post_init__(self) -> None:
        for name in ("event_id", "sensor_id", "modality", "event_kind", "reason", "calibration_status"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        if not isinstance(self.status, SensorEventStatus):
            raise ValueError("status must be a SensorEventStatus")
        if isinstance(self.timestamp_ns, bool) or not isinstance(self.timestamp_ns, int) or self.timestamp_ns < 0:
            raise ValueError("timestamp_ns must be a non-negative integer")
        if self.sequence is not None and (
            isinstance(self.sequence, bool) or not isinstance(self.sequence, int) or self.sequence < 0
        ):
            raise ValueError("sequence must be a non-negative integer when provided")
        for name in ("signal_dbm", "confidence", "evidence_score", "uncertainty_m"):
            value = getattr(self, name)
            if value is not None and not isfinite(value):
                raise ValueError(f"{name} must be finite when provided")
        if self.confidence is not None and not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be in [0, 1]")
        if self.evidence_score is not None and not 0 <= self.evidence_score <= 1:
            raise ValueError("evidence_score must be in [0, 1]")
        if self.uncertainty_m is not None and self.uncertainty_m < 0:
            raise ValueError("uncertainty_m must be non-negative")
        for name in ("model_id", "model_revision", "frame_id"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"{name} must be non-empty when provided")

    def to_dict(self) -> dict[str, str | int | float | None]:
        """Return a JSON-serializable mapping with the status rendered as text."""
        result = asdict(self)
        result["status"] = self.status.value
        return result


class SensorEventLedger:
    """Small deterministic in-memory event ledger with duplicate-ID protection."""

    def __init__(self) -> None:
        self._events: dict[str, SensorEventRecord] = {}

    def append(self, event: SensorEventRecord) -> None:
        if not isinstance(event, SensorEventRecord):
            raise TypeError("event must be a SensorEventRecord")
        if event.event_id in self._events:
            raise ValueError(f"duplicate event_id: {event.event_id}")
        self._events[event.event_id] = event

    def snapshot(
        self, *, now_ns: int, max_age_ns: int | None = None, limit: int = 100
    ) -> tuple[SensorEventRecord, ...]:
        """Return newest-first events, optionally bounded by age and count."""
        if isinstance(now_ns, bool) or not isinstance(now_ns, int) or now_ns < 0:
            raise ValueError("now_ns must be a non-negative integer")
        if max_age_ns is not None and (
            isinstance(max_age_ns, bool) or not isinstance(max_age_ns, int) or max_age_ns < 0
        ):
            raise ValueError("max_age_ns must be a non-negative integer when provided")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 10_000:
            raise ValueError("limit must be an integer from 1 to 10000")
        items = [
            event for event in self._events.values()
            if event.timestamp_ns <= now_ns
            and (max_age_ns is None or now_ns - event.timestamp_ns <= max_age_ns)
        ]
        items.sort(key=lambda event: (event.timestamp_ns, event.sequence or -1, event.event_id), reverse=True)
        return tuple(items[:limit])
