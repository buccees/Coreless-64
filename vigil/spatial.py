"""Dependency-free spatial foundation derived from the VIGIL architecture.

This layer intentionally models information and provenance without requiring a
camera SDK or computer-vision dependency. Concrete perception adapters can be
added later without changing Coreless input contracts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping


@dataclass(frozen=True)
class SpatialPoint:
    x: float
    y: float
    z: float = 0.0
    frame: str = "vigil"


@dataclass(frozen=True)
class CameraFrame:
    source_id: str
    timestamp_ns: int
    sequence: int
    width: int
    height: int
    data: object | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.source_id:
            raise ValueError("source_id must not be empty")
        if self.timestamp_ns < 0 or self.sequence < 0:
            raise ValueError("timestamp_ns and sequence must be non-negative")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("camera dimensions must be positive")


@dataclass(frozen=True)
class Observation:
    observation_id: str
    source_id: str
    timestamp_ns: int
    position: SpatialPoint | None = None
    confidence: float = 1.0
    provenance: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.observation_id or not self.source_id:
            raise ValueError("observation_id and source_id must not be empty")
        if self.timestamp_ns < 0:
            raise ValueError("timestamp_ns must be non-negative")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


class DetectionKind(str, Enum):
    POINTER = "pointer"
    TOUCH = "touch"
    GESTURE = "gesture"
    OBJECT = "object"


@dataclass(frozen=True)
class Detection:
    detection_id: str
    observation: Observation
    kind: DetectionKind
    label: str | None = None
    position: SpatialPoint | None = None
    confidence: float = 1.0

    def __post_init__(self) -> None:
        if not self.detection_id:
            raise ValueError("detection_id must not be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


@dataclass(frozen=True)
class Track:
    track_id: str
    source_ids: tuple[str, ...]
    last_timestamp_ns: int
    position: SpatialPoint | None = None
    confidence: float = 1.0

    def __post_init__(self) -> None:
        if not self.track_id or not self.source_ids:
            raise ValueError("track_id and source_ids must not be empty")
        if self.last_timestamp_ns < 0:
            raise ValueError("last_timestamp_ns must be non-negative")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
