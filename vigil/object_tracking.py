"""Object-level sensor tracking over calibrated spatial observations.

Adapters convert sensor detections into the shared building/model frame. 2.4 GHz
RF ranging is represented separately from acoustic sonar: radio-frequency ranging
is not sonar, and neither modality is assumed to exist without a real adapter.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite, sqrt
from typing import Iterable, Mapping

from .blueprint import BlueprintModel, _validate_vector


class TrackingModality(str, Enum):
    RF_2_4_GHZ = "rf_2_4ghz"
    ACOUSTIC_SONAR = "acoustic_sonar"
    VISION = "vision"
    UWB = "uwb"
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

    def __post_init__(self) -> None:
        if not all((self.object_id.strip(), self.sensor_id.strip(), self.model_id.strip(),
                    self.model_revision.strip(), self.frame_id.strip(), self.provenance.strip())):
            raise ValueError("object, sensor, model, frame, and provenance are required")
        if self.timestamp_ns < 0:
            raise ValueError("timestamp_ns must be non-negative")
        _validate_vector(self.position_m, "object position")
        if not isfinite(self.uncertainty_m) or self.uncertainty_m <= 0:
            raise ValueError("uncertainty_m must be finite and positive")
        if not isinstance(self.modality, TrackingModality):
            raise ValueError("modality must be a TrackingModality")


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


class ObjectTracker:
    """Deterministic, bounded-lifetime object tracker; not a sensor driver.

    Input positions must already be calibrated into the active model frame.
    Tracks expire when no fresh observations remain. Velocity is estimated from
    successive filtered positions, with a bounded alpha update to damp jitter.
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
            fresh.setdefault(item.object_id, []).append(item)

        updated: dict[str, ObjectTrack] = {}
        for object_id, observations_for_object in fresh.items():
            # Fuse only detections from the newest measurement epoch. Combining
            # old and new positions into one average would smear motion and bias
            # both the reported position and velocity.
            timestamp = max(item.timestamp_ns for item in observations_for_object)
            group = [item for item in observations_for_object if item.timestamp_ns == timestamp]
            weights = [1.0 / (item.uncertainty_m ** 2) for item in group]
            total = sum(weights)
            measured = tuple(
                sum(w * item.position_m[axis] for w, item in zip(weights, group)) / total
                for axis in range(3)
            )
            measurement_uncertainty = sqrt(1.0 / total)
            previous = self._tracks.get(object_id)
            if previous is None:
                position = measured
                velocity = (0.0, 0.0, 0.0)
                uncertainty = measurement_uncertainty
                count = len(group)
            else:
                dt_ns = timestamp - previous.last_seen_ns
                if dt_ns <= 0:
                    # Do not rewind a track or double-count a repeated timestamp.
                    updated[object_id] = previous
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
            updated[object_id] = ObjectTrack(
                object_id=object_id, model_id=model.model_id, model_revision=model.revision,
                frame_id=model.frame_id, position_m=position, velocity_mps=velocity,
                uncertainty_m=uncertainty, last_seen_ns=timestamp,
                sensor_ids=tuple(sorted({item.sensor_id for item in group})),
                modalities=tuple(sorted({item.modality.value for item in group})),
                observation_count=count,
            )

        # Retain only fresh tracks, then bound memory by most recently seen.
        for object_id, track in self._tracks.items():
            if now_ns - track.last_seen_ns <= max_age_ns and object_id not in updated:
                updated[object_id] = track
        ordered = sorted(updated.values(), key=lambda track: track.last_seen_ns, reverse=True)
        self._tracks = {track.object_id: track for track in ordered[:self.max_tracks]}
        return tuple(sorted(self._tracks.values(), key=lambda track: track.object_id))

    def clear(self) -> None:
        self._tracks.clear()
