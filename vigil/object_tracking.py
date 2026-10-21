"""Object-level sensor tracking over calibrated spatial observations.

Adapters convert sensor detections into the shared building/model frame. 2.4 GHz
RF ranging is represented separately from acoustic sonar: radio-frequency ranging
is not sonar, and neither modality is assumed to exist without a real adapter.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite, sqrt
from typing import Iterable

from .blueprint import BlueprintModel, _validate_vector


class TrackingModality(str, Enum):
    RF_2_4_GHZ = "rf_2_4ghz"
    ACOUSTIC_SONAR = "acoustic_sonar"
    VISION = "vision"
    UWB = "uwb"
    INFRARED = "infrared"
    OTHER = "other"


@dataclass(frozen=True)
class ObjectObservation:
    object_id: str
    sensor_id: str
    model_id: str
    model_revision: str
    frame_id: str
    timestamp_ns: int
    position_m: tuple[float, float, float]
    uncertainty_m: float
    modality: TrackingModality
    provenance: str
    # Sensors may use different local detection IDs. Only a shared, upstream
    # association ID explicitly asserts that those detections refer to one entity.
    association_id: str | None = None

    def __post_init__(self) -> None:
        if not all((self.object_id.strip(), self.sensor_id.strip(), self.model_id.strip(),
                    self.model_revision.strip(), self.frame_id.strip(), self.provenance.strip())):
            raise ValueError("object, sensor, model, frame, and provenance are required")
        if self.association_id is not None and not self.association_id.strip():
            raise ValueError("association_id must be non-empty when provided")
        if self.timestamp_ns < 0:
            raise ValueError("timestamp_ns must be non-negative")
        _validate_vector(self.position_m, "object position")
        if not isfinite(self.uncertainty_m) or self.uncertainty_m <= 0:
            raise ValueError("uncertainty_m must be finite and positive")
        if not isinstance(self.modality, TrackingModality):
            raise ValueError("modality must be a TrackingModality")

    @property
    def tracking_key(self) -> str:
        """Namespace explicit associations separately from sensor-local object IDs."""
        return f"association:{self.association_id}" if self.association_id else f"object:{self.object_id}"


@dataclass(frozen=True)
class ObjectTrack:
    object_id: str
    model_id: str
    model_revision: str
    frame_id: str
    position_m: tuple[float, float, float]
    velocity_mps: tuple[float, float, float]
    uncertainty_m: float
    last_seen_ns: int
    sensor_ids: tuple[str, ...]
    modalities: tuple[str, ...]
    observation_count: int
    association_id: str | None = None
    provenance: tuple[str, ...] = ()


class ObjectTracker:
    """Deterministic, bounded-lifetime tracker with conservative cross-sensor fusion.

    Cross-sensor detections merge only when their object IDs match or the adapters
    supply the same explicit association_id. Spatial proximity alone never proves
    identity. Positions from the newest timestamp epoch are inverse-variance fused;
    track metadata accumulates the contributing sensors, modalities, and provenance.
    """

    def __init__(self, *, alpha: float = 0.65, max_tracks: int = 256) -> None:
        if not isfinite(alpha) or not 0 < alpha <= 1:
            raise ValueError("alpha must be finite and in (0, 1]")
        if max_tracks < 1:
            raise ValueError("max_tracks must be positive")
        self.alpha = alpha
        self.max_tracks = max_tracks
        self._tracks: dict[str, ObjectTrack] = {}

    def update(
        self,
        model: BlueprintModel,
        observations: Iterable[ObjectObservation],
        *,
        now_ns: int,
        max_age_ns: int = 1_000_000_000,
    ) -> tuple[ObjectTrack, ...]:
        if now_ns < 0 or max_age_ns < 0:
            raise ValueError("time values must be non-negative")
        fresh: dict[str, list[ObjectObservation]] = {}
        for item in observations:
            if (item.model_id, item.model_revision, item.frame_id) != (
                model.model_id, model.revision, model.frame_id
            ):
                continue
            if item.timestamp_ns > now_ns or now_ns - item.timestamp_ns > max_age_ns:
                continue
            fresh.setdefault(item.tracking_key, []).append(item)

        updated: dict[str, ObjectTrack] = {}
        for tracking_key, observations_for_object in fresh.items():
            # Fuse only the newest measurement epoch to avoid smearing motion.
            timestamp = max(item.timestamp_ns for item in observations_for_object)
            group = [item for item in observations_for_object if item.timestamp_ns == timestamp]
            weights = [1.0 / (item.uncertainty_m ** 2) for item in group]
            total = sum(weights)
            measured = tuple(
                sum(w * item.position_m[axis] for w, item in zip(weights, group)) / total
                for axis in range(3)
            )
            measurement_uncertainty = sqrt(1.0 / total)
            previous = self._tracks.get(tracking_key)
            if previous is None:
                position = measured
                velocity = (0.0, 0.0, 0.0)
                uncertainty = measurement_uncertainty
                count = len(group)
                object_id = group[0].object_id
                old_sensors: set[str] = set()
                old_modalities: set[str] = set()
                old_provenance: set[str] = set()
            else:
                dt_ns = timestamp - previous.last_seen_ns
                if dt_ns <= 0:
                    updated[tracking_key] = previous
                    continue
                dt = dt_ns / 1_000_000_000
                position = tuple(
                    old + self.alpha * (new - old)
                    for old, new in zip(previous.position_m, measured)
                )
                velocity = tuple(
                    (position[axis] - previous.position_m[axis]) / dt
                    for axis in range(3)
                )
                uncertainty = sqrt(
                    (1 - self.alpha) ** 2 * previous.uncertainty_m ** 2
                    + self.alpha ** 2 * measurement_uncertainty ** 2
                )
                count = previous.observation_count + len(group)
                object_id = previous.object_id
                old_sensors = set(previous.sensor_ids)
                old_modalities = set(previous.modalities)
                old_provenance = set(previous.provenance)
            updated[tracking_key] = ObjectTrack(
                object_id=object_id, model_id=model.model_id, model_revision=model.revision,
                frame_id=model.frame_id, position_m=position, velocity_mps=velocity,
                uncertainty_m=uncertainty, last_seen_ns=timestamp,
                sensor_ids=tuple(sorted(old_sensors | {item.sensor_id for item in group})),
                modalities=tuple(sorted(old_modalities | {item.modality.value for item in group})),
                observation_count=count,
                association_id=group[0].association_id,
                provenance=tuple(sorted(old_provenance | {item.provenance for item in group})),
            )

        # Retain only fresh tracks, then bound memory by most recently seen.
        for tracking_key, track in self._tracks.items():
            if now_ns - track.last_seen_ns <= max_age_ns and tracking_key not in updated:
                updated[tracking_key] = track
        ordered = sorted(updated.items(), key=lambda pair: pair[1].last_seen_ns, reverse=True)
        self._tracks = dict(ordered[:self.max_tracks])
        return tuple(sorted(self._tracks.values(), key=lambda track: (track.object_id, track.association_id or "")))

    def clear(self) -> None:
        self._tracks.clear()
