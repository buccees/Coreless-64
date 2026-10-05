"""Coreless-native VIGIL information model.

The model deliberately separates observations, detections, tracks, world entities,
and derived interpretations. It preserves time, confidence, uncertainty, and
provenance rather than collapsing them into a single score.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping


class SensorState(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    STALE = "stale"
    UNAVAILABLE = "unavailable"
    INVALID = "invalid"
    CALIBRATION_UNCERTAIN = "calibration_uncertain"
    TIMESTAMP_UNCERTAIN = "timestamp_uncertain"


class EntityType(str, Enum):
    UNKNOWN = "unknown"
    PERSON = "person"
    OBJECT = "object"
    AREA = "area"
    SENSOR = "sensor"
    TARGET = "target"


@dataclass(frozen=True)
class Uncertainty:
    position_m: float | None = None
    time_ns: int | None = None
    classification: float | None = None

    def __post_init__(self) -> None:
        for value in (self.position_m, self.classification):
            if value is not None and value < 0:
                raise ValueError("uncertainty values must be non-negative")
        if self.time_ns is not None and self.time_ns < 0:
            raise ValueError("time uncertainty must be non-negative")


@dataclass(frozen=True)
class Provenance:
    source_id: str
    source_type: str
    created_ns: int
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.source_id or not self.source_type:
            raise ValueError("source_id and source_type must not be empty")
        if self.created_ns < 0:
            raise ValueError("created_ns must be non-negative")


@dataclass(frozen=True)
class Observation:
    observation_id: str
    source_id: str
    timestamp_ns: int
    payload: Mapping[str, object] = field(default_factory=dict)
    confidence: float = 1.0
    uncertainty: Uncertainty = field(default_factory=Uncertainty)
    provenance: Provenance | None = None
    sensor_state: SensorState = SensorState.HEALTHY

    def __post_init__(self) -> None:
        if not self.observation_id or not self.source_id:
            raise ValueError("observation_id and source_id must not be empty")
        if self.timestamp_ns < 0:
            raise ValueError("timestamp_ns must be non-negative")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


@dataclass(frozen=True)
class Detection:
    detection_id: str
    observation_id: str
    entity_type: EntityType
    label: str | None
    timestamp_ns: int
    position: tuple[float, float, float] | None = None
    confidence: float = 1.0
    uncertainty: Uncertainty = field(default_factory=Uncertainty)
    provenance: tuple[Provenance, ...] = ()

    def __post_init__(self) -> None:
        if not self.detection_id or not self.observation_id:
            raise ValueError("detection_id and observation_id must not be empty")
        if self.timestamp_ns < 0:
            raise ValueError("timestamp_ns must be non-negative")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


@dataclass(frozen=True)
class Track:
    track_id: str
    detection_ids: tuple[str, ...]
    last_timestamp_ns: int
    position: tuple[float, float, float] | None
    confidence: float
    velocity: tuple[float, float, float] | None = None

    def __post_init__(self) -> None:
        if not self.track_id or not self.detection_ids:
            raise ValueError("track_id and detection_ids must not be empty")
        if self.last_timestamp_ns < 0:
            raise ValueError("last_timestamp_ns must be non-negative")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


@dataclass(frozen=True)
class WorldEntity:
    entity_id: str
    entity_type: EntityType
    label: str | None
    position: tuple[float, float, float] | None
    track_id: str | None
    confidence: float
    uncertainty: Uncertainty
    provenance: tuple[Provenance, ...]
    first_seen_ns: int
    last_seen_ns: int
    valid: bool = True
    fresh: bool = True
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.entity_id:
            raise ValueError("entity_id must not be empty")
        if self.first_seen_ns < 0 or self.last_seen_ns < self.first_seen_ns:
            raise ValueError("invalid entity timestamps")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
