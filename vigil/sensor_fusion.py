"""Time-aligned multi-sensor evidence coordination for VIGIL.

Only calibrated spatial observations can update object positions. Wi-Fi CSI
motion scores and infrared floor maps are retained as contextual evidence and
quality gates; neither is silently converted into a 3D object detection.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Sequence

from .blueprint import BlueprintModel
from .csi_pipeline import CsiPipelineResult
from .infrared_floor_mapping import InfraredFloorMap
from .object_tracking import ObjectObservation, ObjectTrack, ObjectTracker


@dataclass(frozen=True)
class SensorFusionSnapshot:
    timestamp_ns: int
    tracks: tuple[ObjectTrack, ...]
    active_csi_sensors: tuple[str, ...]
    infrared_levels: tuple[str, ...]
    accepted_observation_count: int
    rejected_observation_count: int
    rejected_csi_count: int
    rejected_infrared_count: int
    notes: tuple[str, ...]


class MultiSensorFusion:
    """Coordinate fresh, model-aligned sensor evidence without inventing detections."""

    def __init__(
        self,
        model: BlueprintModel,
        *,
        tracker: ObjectTracker | None = None,
        max_age_ns: int = 1_000_000_000,
        max_csi_skew_ns: int = 250_000_000,
        max_ir_age_ns: int = 2_000_000_000,
    ) -> None:
        for name, value in (("max_age_ns", max_age_ns),
                            ("max_csi_skew_ns", max_csi_skew_ns),
                            ("max_ir_age_ns", max_ir_age_ns)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        self.model = model
        self.tracker = tracker or ObjectTracker()
        self.max_age_ns = max_age_ns
        self.max_csi_skew_ns = max_csi_skew_ns
        self.max_ir_age_ns = max_ir_age_ns

    def fuse(
        self,
        *,
        now_ns: int,
        observations: Sequence[ObjectObservation] = (),
        csi_results: Sequence[CsiPipelineResult] = (),
        infrared_maps: Sequence[InfraredFloorMap] = (),
    ) -> SensorFusionSnapshot:
        """Fuse a snapshot; CSI/IR add context while positions come from observations."""
        if isinstance(now_ns, bool) or not isinstance(now_ns, int) or now_ns < 0:
            raise ValueError("now_ns must be a non-negative integer")

        accepted: list[ObjectObservation] = []
        rejected_observations = 0
        for item in observations:
            aligned = (item.model_id, item.model_revision, item.frame_id) == (
                self.model.model_id, self.model.revision, self.model.frame_id
            )
            fresh = 0 <= now_ns - item.timestamp_ns <= self.max_age_ns
            if aligned and fresh:
                accepted.append(item)
            else:
                rejected_observations += 1

        active_csi: set[str] = set()
        rejected_csi = 0
        for result in csi_results:
            age = now_ns - result.timestamp_ns
            if age < 0 or age > self.max_csi_skew_ns:
                rejected_csi += 1
                continue
            if result.motion.active:
                active_csi.add(result.sensor_id)

        infrared_levels: set[str] = set()
        rejected_ir = 0
        for floor_map in infrared_maps:
            aligned = (floor_map.model_id, floor_map.model_revision, floor_map.frame_id) == (
                self.model.model_id, self.model.revision, self.model.frame_id
            )
            age = now_ns - floor_map.timestamp_ns
            if not aligned or age < 0 or age > self.max_ir_age_ns:
                rejected_ir += 1
                continue
            infrared_levels.add(floor_map.level_id)

        tracks = self.tracker.update(
            self.model, accepted, now_ns=now_ns, max_age_ns=self.max_age_ns
        )
        notes: list[str] = []
        if active_csi:
            notes.append("CSI indicates motion-like channel change; it does not identify or locate an object.")
        if infrared_levels:
            notes.append("Infrared maps are calibrated floor context; mapped pixels are not automatically object tracks.")
        if rejected_observations:
            notes.append("Some spatial observations were rejected for age or model/frame mismatch.")
        if rejected_csi:
            notes.append("Some CSI evidence was rejected for time skew or future timestamps.")
        if rejected_ir:
            notes.append("Some infrared maps were rejected for age or model/frame mismatch.")
        if not accepted:
            notes.append("No accepted spatial observations; no new object position was inferred.")
        return SensorFusionSnapshot(
            timestamp_ns=now_ns,
            tracks=tracks,
            active_csi_sensors=tuple(sorted(active_csi)),
            infrared_levels=tuple(sorted(infrared_levels)),
            accepted_observation_count=len(accepted),
            rejected_observation_count=rejected_observations,
            rejected_csi_count=rejected_csi,
            rejected_infrared_count=rejected_ir,
            notes=tuple(notes),
        )
