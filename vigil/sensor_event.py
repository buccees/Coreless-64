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
    independence_group: str | None = None
    lineage_declared: bool = False

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
        if self.independence_group is not None and (not isinstance(self.independence_group, str) or not self.independence_group.strip()):
            raise ValueError("independence_group must be non-empty when provided")
        if not isinstance(self.lineage_declared, bool):
            raise ValueError("lineage_declared must be a boolean")
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
    """In-memory ledger with duplicate, per-sensor ordering, and late-arrival checks.

    Timestamps are source event times, not ingestion times. Default late-arrival
    tolerance is zero. An explicitly allowed late event is retained with a warning;
    the per-sensor timestamp watermark never moves backwards.
    """

    def __init__(
        self,
        *,
        allowed_lateness_ns: int = 0,
        clock_offsets_ns: dict[str, int] | None = None,
    ) -> None:
        if isinstance(allowed_lateness_ns, bool) or not isinstance(allowed_lateness_ns, int) or allowed_lateness_ns < 0:
            raise ValueError("allowed_lateness_ns must be a non-negative integer")
        self.allowed_lateness_ns = allowed_lateness_ns
        self.clock_offsets_ns: dict[str, int] = {}
        for sensor_id, offset in (clock_offsets_ns or {}).items():
            if not isinstance(sensor_id, str) or not sensor_id.strip():
                raise ValueError("clock offset sensor IDs must be non-empty strings")
            if isinstance(offset, bool) or not isinstance(offset, int):
                raise ValueError("clock offsets must be integer nanoseconds")
            self.clock_offsets_ns[sensor_id] = offset
        self._events: dict[str, SensorEventRecord] = {}
        self._alignment: dict[str, dict[str, str | int | None]] = {}
        self._aligned_timestamp: dict[str, int] = {}
        self._latest_timestamp: dict[str, int] = {}
        self._latest_sequence: dict[str, int] = {}

    def append(self, event: SensorEventRecord) -> None:
        if not isinstance(event, SensorEventRecord):
            raise TypeError("event must be a SensorEventRecord")
        if event.event_id in self._events:
            raise ValueError(f"duplicate event_id: {event.event_id}")
        clock_offset = self.clock_offsets_ns.get(event.sensor_id, 0)
        aligned_timestamp = event.timestamp_ns + clock_offset
        if aligned_timestamp < 0:
            raise ValueError("clock offset would produce a negative aligned timestamp")
        latest_timestamp = self._latest_timestamp.get(event.sensor_id)
        latest_sequence = self._latest_sequence.get(event.sensor_id)
        if event.sequence is not None and latest_sequence is not None and event.sequence <= latest_sequence:
            raise ValueError(f"out-of-order sequence for sensor {event.sensor_id}: {event.sequence} <= {latest_sequence}")
        alignment: dict[str, str | int | None] = {
            "status": "aligned",
            "reason": "first event for sensor" if latest_timestamp is None else "timestamp and sequence checks passed",
            "lateness_ns": 0,
            "clock_offset_ns": clock_offset,
            "aligned_timestamp_ns": aligned_timestamp,
        }
        if latest_timestamp is not None and aligned_timestamp < latest_timestamp:
            lateness = latest_timestamp - aligned_timestamp
            if lateness > self.allowed_lateness_ns:
                raise ValueError(
                    f"late event for sensor {event.sensor_id}: {lateness} ns exceeds "
                    f"allowed tolerance {self.allowed_lateness_ns} ns"
                )
            alignment = {
                "status": "late_within_tolerance",
                "reason": "event arrived behind the sensor watermark; retained with warning",
                "lateness_ns": lateness,
                "clock_offset_ns": clock_offset,
                "aligned_timestamp_ns": aligned_timestamp,
            }
        self._events[event.event_id] = event
        self._alignment[event.event_id] = alignment
        self._aligned_timestamp[event.event_id] = aligned_timestamp
        self._latest_timestamp[event.sensor_id] = max(aligned_timestamp, latest_timestamp or 0)
        if event.sequence is not None:
            self._latest_sequence[event.sensor_id] = event.sequence

    def alignment_for(self, event_id: str) -> dict[str, str | int | None]:
        """Return explicit ordering metadata without mutating the source event."""
        if event_id not in self._alignment:
            raise KeyError(f"unknown event_id: {event_id}")
        return dict(self._alignment[event_id])
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
            if self._aligned_timestamp[event.event_id] <= now_ns
            and (max_age_ns is None or now_ns - self._aligned_timestamp[event.event_id] <= max_age_ns)
        ]
        items.sort(key=lambda event: (self._aligned_timestamp[event.event_id], event.sequence or -1, event.event_id), reverse=True)
        return tuple(items[:limit])
