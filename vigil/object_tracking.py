"""Object-level sensor tracking over calibrated spatial observations.

Adapters convert sensor detections into the shared building/model frame. 2.4 GHz
RF ranging is represented separately from acoustic sonar: radio-frequency ranging
is not sonar, and neither modality is assumed to exist without a real adapter.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
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
    # Sensors sharing this token are treated as one evidence source for
    # conflict resolution (e.g. two derived feeds from one physical receiver).
    independence_group: str | None = None
    calibration_status: str = "unverified"
    calibration_ids: tuple[str, ...] = ()
    lineage_declared: bool = False

    def __post_init__(self) -> None:
        if not all((self.object_id.strip(), self.sensor_id.strip(), self.model_id.strip(),
                    self.model_revision.strip(), self.frame_id.strip(), self.provenance.strip())):
            raise ValueError("object, sensor, model, frame, and provenance are required")
        if self.association_id is not None and not self.association_id.strip():
            raise ValueError("association_id must be non-empty when provided")
        if self.independence_group is not None and not self.independence_group.strip():
            raise ValueError("independence_group must be non-empty when provided")
        if self.calibration_status not in ("verified", "unverified", "failed"):
            raise ValueError("calibration_status must be verified, unverified, or failed")
        if any(not isinstance(value, str) or not value.strip() for value in self.calibration_ids):
            raise ValueError("calibration_ids must contain non-empty strings")
        if not isinstance(self.lineage_declared, bool):
            raise ValueError("lineage_declared must be a boolean")
        if self.timestamp_ns < 0:
            raise ValueError("timestamp_ns must be non-negative")
        _validate_vector(self.position_m, "object position")
        if not isfinite(self.uncertainty_m) or self.uncertainty_m <= 0:
            raise ValueError("uncertainty_m must be finite and positive")
        if not isinstance(self.modality, TrackingModality):
            raise ValueError("modality must be a TrackingModality")

    @property
    def evidence_independence_group(self) -> str:
        """Return declared source lineage, or sensor ID as a compatibility default.

        The default preserves existing behavior; it does not certify physical
        independence. Adapters should share a group when feeds share a source.
        """
        return self.independence_group or self.sensor_id

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
    conflict: bool = False
    conflict_reasons: tuple[str, ...] = ()
    conflicting_sensor_ids: tuple[str, ...] = ()
    # Declared evidence lineage tokens accumulated across this track.
    independence_groups: tuple[str, ...] = ()
    # Timestamped positions in the same model frame, oldest first.
    position_history_m: tuple[tuple[int, tuple[float, float, float]], ...] = ()
    # Sensor IDs contributing to each timestamped position; aligned by timestamp.
    position_history_sensor_ids: tuple[tuple[int, tuple[str, ...]], ...] = ()
    calibration_status: str = "unverified"
    calibration_ids: tuple[str, ...] = ()
    lineage_declared: bool = False


class ObjectTracker:
    """Deterministic, bounded-lifetime tracker with conservative cross-sensor fusion.

    Cross-sensor detections merge only when their object IDs match or the adapters
    supply the same explicit association_id. Spatial proximity alone never proves
    identity. Positions from the newest timestamp epoch are inverse-variance fused;
    track metadata accumulates sensors, modalities, provenance, and evidence groups.
    Conflict resolution counts distinct independence groups, not just sensor IDs.
    Unspecified groups default to sensor_id for compatibility; that default does not
    prove that two physical sources are independent.
    """

    def __init__(
        self, *, alpha: float = 0.65, max_tracks: int = 256,
        max_position_disagreement_m: float = 2.0,
        max_fusion_skew_ns: int = 100_000_000,
        max_history_points: int = 32,
        conflict_resolution_min_sensors: int = 2,
    ) -> None:
        if not isfinite(alpha) or not 0 < alpha <= 1:
            raise ValueError("alpha must be finite and in (0, 1]")
        if max_tracks < 1:
            raise ValueError("max_tracks must be positive")
        if isinstance(max_history_points, bool) or not isinstance(max_history_points, int) or max_history_points < 1:
            raise ValueError("max_history_points must be a positive integer")
        if not isfinite(max_position_disagreement_m) or max_position_disagreement_m <= 0:
            raise ValueError("max_position_disagreement_m must be finite and positive")
        if isinstance(max_fusion_skew_ns, bool) or not isinstance(max_fusion_skew_ns, int) or max_fusion_skew_ns < 0:
            raise ValueError("max_fusion_skew_ns must be a non-negative integer")
        if (isinstance(conflict_resolution_min_sensors, bool)
                or not isinstance(conflict_resolution_min_sensors, int)
                or conflict_resolution_min_sensors < 2):
            raise ValueError("conflict_resolution_min_sensors must be an integer of at least 2")
        self.alpha = alpha
        self.max_tracks = max_tracks
        self.max_position_disagreement_m = max_position_disagreement_m
        self.max_fusion_skew_ns = max_fusion_skew_ns
        self.max_history_points = max_history_points
        self.conflict_resolution_min_sensors = conflict_resolution_min_sensors
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
            conflict_reasons: set[str] = set()
            if max(item.timestamp_ns for item in observations_for_object) - min(
                item.timestamp_ns for item in observations_for_object
            ) > self.max_fusion_skew_ns:
                conflict_reasons.add("timestamp_skew")
            conflicting_sensors: set[str] = set()
            for index, left in enumerate(group):
                for right in group[index + 1:]:
                    separation = sqrt(sum(
                        (left.position_m[axis] - right.position_m[axis]) ** 2
                        for axis in range(3)
                    ))
                    tolerance = self.max_position_disagreement_m + 3.0 * sqrt(
                        left.uncertainty_m ** 2 + right.uncertainty_m ** 2
                    )
                    if separation > tolerance:
                        conflict_reasons.add("position_disagreement")
                        conflicting_sensors.update((left.sensor_id, right.sensor_id))
            if conflict_reasons:
                # Keep the most precise newest observation as the display estimate;
                # never average contradictory measurements into a misleading midpoint.
                selected = min(group, key=lambda item: item.uncertainty_m)
                measured = selected.position_m
                measurement_uncertainty = selected.uncertainty_m
                if not conflicting_sensors:
                    conflicting_sensors.update(item.sensor_id for item in observations_for_object)
            else:
                weights = [1.0 / (item.uncertainty_m ** 2) for item in group]
                total = sum(weights)
                measured = tuple(
                    sum(w * item.position_m[axis] for w, item in zip(weights, group)) / total
                    for axis in range(3)
                )
                measurement_uncertainty = sqrt(1.0 / total)
            previous = self._tracks.get(tracking_key)
            current_sensor_ids = {item.sensor_id for item in group}
            current_independence_groups = {item.evidence_independence_group for item in group}
            # A conflict remains unresolved until a later, clean measurement epoch
            # is corroborated by enough distinct declared evidence groups.
            can_resolve_previous_conflict = (
                previous is not None
                and timestamp > previous.last_seen_ns
                and not conflict_reasons
                and len(current_independence_groups) >= self.conflict_resolution_min_sensors
            )
            unresolved_previous_conflict = (
                previous is not None and previous.conflict
                and not can_resolve_previous_conflict
            )
            effective_conflict_reasons = set(conflict_reasons)
            effective_conflicting_sensors = set(conflicting_sensors)
            if unresolved_previous_conflict:
                effective_conflict_reasons.update(previous.conflict_reasons)
                effective_conflicting_sensors.update(previous.conflicting_sensor_ids)
            if previous is None:
                position = measured
                velocity = (0.0, 0.0, 0.0)
                uncertainty = measurement_uncertainty
                count = len(group)
                object_id = group[0].object_id
                old_sensors: set[str] = set()
                old_modalities: set[str] = set()
                old_provenance: set[str] = set()
                old_independence_groups: set[str] = set()
                old_calibration_ids: set[str] = set()
                old_calibration_status = "verified"
                old_lineage_declared = True
            else:
                dt_ns = timestamp - previous.last_seen_ns
                if dt_ns <= 0:
                    # A newly arriving sensor may disagree at the same timestamp
                    # as an existing track. Preserve its motion estimate, but do
                    # not silently discard the conflict or its source evidence.
                    current_sources = observations_for_object
                    updated[tracking_key] = replace(
                        previous,
                        sensor_ids=tuple(sorted(set(previous.sensor_ids) | {
                            item.sensor_id for item in current_sources
                        })),
                        modalities=tuple(sorted(set(previous.modalities) | {
                            item.modality.value for item in current_sources
                        })),
                        provenance=tuple(sorted(set(previous.provenance) | {
                            item.provenance for item in current_sources
                        })),
                        independence_groups=tuple(sorted(set(previous.independence_groups) | {
                            item.evidence_independence_group for item in current_sources
                        })),
                        calibration_status=("failed" if previous.calibration_status == "failed" or any(item.calibration_status == "failed" for item in current_sources) else "unverified" if previous.calibration_status == "unverified" or any(item.calibration_status == "unverified" for item in current_sources) else "verified"),
                        calibration_ids=tuple(sorted(set(previous.calibration_ids) | {value for item in current_sources for value in item.calibration_ids})),
                        lineage_declared=previous.lineage_declared and all(item.lineage_declared for item in current_sources),
                        conflict=bool(effective_conflict_reasons),
                        conflict_reasons=tuple(sorted(effective_conflict_reasons)),
                        conflicting_sensor_ids=tuple(sorted(
                            effective_conflicting_sensors or (
                                {item.sensor_id for item in current_sources}
                                if effective_conflict_reasons else set()
                            )
                        )),
                        position_history_sensor_ids=(
                            previous.position_history_sensor_ids[:-1] + ((
                                previous.position_history_sensor_ids[-1][0],
                                tuple(sorted(set(previous.position_history_sensor_ids[-1][1]) | {
                                    item.sensor_id for item in current_sources
                                })),
                            ),)
                            if previous.position_history_sensor_ids
                            and previous.position_history_sensor_ids[-1][0] == timestamp
                            else previous.position_history_sensor_ids
                        ),
                    )
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
                old_independence_groups = set(previous.independence_groups)
                old_calibration_ids = set(previous.calibration_ids)
                old_calibration_status = previous.calibration_status
                old_lineage_declared = previous.lineage_declared
            updated[tracking_key] = ObjectTrack(
                object_id=object_id, model_id=model.model_id, model_revision=model.revision,
                frame_id=model.frame_id, position_m=position, velocity_mps=velocity,
                uncertainty_m=uncertainty, last_seen_ns=timestamp,
                sensor_ids=tuple(sorted(old_sensors | {item.sensor_id for item in group})),
                modalities=tuple(sorted(old_modalities | {item.modality.value for item in group})),
                observation_count=count,
                association_id=group[0].association_id,
                provenance=tuple(sorted(old_provenance | {item.provenance for item in group})),
                conflict=bool(effective_conflict_reasons),
                conflict_reasons=tuple(sorted(effective_conflict_reasons)),
                conflicting_sensor_ids=tuple(sorted(effective_conflicting_sensors)),
                independence_groups=tuple(sorted(old_independence_groups | {
                    item.evidence_independence_group for item in group
                })),
                calibration_status=("failed" if old_calibration_status == "failed" or any(item.calibration_status == "failed" for item in group) else "unverified" if old_calibration_status == "unverified" or any(item.calibration_status == "unverified" for item in group) else "verified"),
                calibration_ids=tuple(sorted(old_calibration_ids | {value for item in group for value in item.calibration_ids})),
                lineage_declared=old_lineage_declared and all(item.lineage_declared for item in group),
                position_history_m=(
                    ((timestamp, position),) if previous is None else
                    (previous.position_history_m + ((timestamp, position),))[-self.max_history_points:]
                ),
                position_history_sensor_ids=(
                    ((timestamp, tuple(sorted({item.sensor_id for item in group}))),)
                    if previous is None else
                    (previous.position_history_sensor_ids + ((
                        timestamp, tuple(sorted({item.sensor_id for item in group}))
                    ),))[-self.max_history_points:]
                ),
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
