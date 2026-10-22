"""Unified spatial-scene assembly with visible multi-sensor status and warnings."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .blueprint import BlueprintModel, PoseEstimate
from .csi_pipeline import CsiPipelineResult
from .infrared_floor_mapping import InfraredFloorMap
from .object_tracking import ObjectObservation, ObjectTrack, ObjectTracker
from .sensor_fusion import MultiSensorFusion, SensorFusionSnapshot
from .spatial_scene import SpatialScene, assemble_spatial_scene


@dataclass(frozen=True)
class SensorStatus:
    sensor_family: str
    status: str
    detail: str


@dataclass(frozen=True)
class FusedSpatialScene:
    scene: SpatialScene
    evidence: SensorFusionSnapshot
    sensor_status: tuple[SensorStatus, ...]
    warnings: tuple[str, ...]

    @property
    def ready(self) -> bool:
        """Readiness remains governed by spatial_scene's explicit quality checks."""
        return self.scene.finishing_move_ready


def assemble_fused_spatial_scene(
    model: BlueprintModel | None,
    pose: PoseEstimate | None,
    *,
    selected_level: str | None,
    now_ns: int,
    observations: Sequence[ObjectObservation] = (),
    csi_results: Sequence[CsiPipelineResult] = (),
    infrared_maps: Sequence[InfraredFloorMap] = (),
    tracker: ObjectTracker | None = None,
    max_pose_age_ns: int = 2_000_000_000,
    max_object_age_ns: int = 2_000_000_000,
    max_ir_age_ns: int = 2_000_000_000,
    max_csi_skew_ns: int = 250_000_000,
    max_pose_uncertainty_m: float = 2.0,
    require_conflict_free_tracks: bool = True,
) -> FusedSpatialScene:
    """Fuse evidence first, then assemble one scene and a readable sensor-status panel."""
    if model is None:
        # No model means there is no safe coordinate frame for fusion. Keep an
        # explicit empty snapshot so callers can still render a denied scene.
        from .sensor_fusion import SensorFusionSnapshot
        evidence = SensorFusionSnapshot(
            timestamp_ns=now_ns, tracks=(), active_csi_sensors=(), infrared_levels=(),
            accepted_observation_count=0, rejected_observation_count=len(observations),
            rejected_csi_count=len(csi_results), rejected_infrared_count=len(infrared_maps),
            notes=("No active blueprint; sensor data cannot be aligned to a model frame.",),
        )
        scene = assemble_spatial_scene(
            None, pose, selected_level=selected_level, now_ns=now_ns,
            max_pose_age_ns=max_pose_age_ns, max_object_age_ns=max_object_age_ns,
            max_ir_age_ns=max_ir_age_ns, max_pose_uncertainty_m=max_pose_uncertainty_m,
            require_conflict_free_tracks=require_conflict_free_tracks,
        )
    else:
        fusion = MultiSensorFusion(
            model, tracker=tracker, max_age_ns=max_object_age_ns,
            max_csi_skew_ns=max_csi_skew_ns, max_ir_age_ns=max_ir_age_ns,
        )
        evidence = fusion.fuse(
            now_ns=now_ns, observations=observations,
            csi_results=csi_results, infrared_maps=infrared_maps,
        )
        scene = assemble_spatial_scene(
            model, pose, evidence.tracks, infrared_maps,
            selected_level=selected_level, now_ns=now_ns,
            max_pose_age_ns=max_pose_age_ns, max_object_age_ns=max_object_age_ns,
            max_ir_age_ns=max_ir_age_ns, max_pose_uncertainty_m=max_pose_uncertainty_m,
            require_conflict_free_tracks=require_conflict_free_tracks,
        )

    csi_count = len(csi_results) - evidence.rejected_csi_count
    ir_count = len(evidence.infrared_levels)
    statuses = (
        SensorStatus(
            "2.4 GHz Wi-Fi CSI",
            "MOTION EVIDENCE" if evidence.active_csi_sensors else (
                "NO ACTIVE MOTION FLAG" if csi_count else "STALE / REJECTED / NOT PROVIDED"
            ),
            (", ".join(evidence.active_csi_sensors) if evidence.active_csi_sensors
             else f"{csi_count} fresh sample(s); CSI is contextual evidence, not a position fix."),
        ),
        SensorStatus(
            "Infrared floor mapping",
            "ALIGNED" if ir_count else ("STALE / REJECTED / NOT PROVIDED" if evidence.rejected_infrared_count or not infrared_maps else "NO VALID FLOOR MAP"),
            f"{ir_count} aligned floor(s): {', '.join(evidence.infrared_levels) if ir_count else 'none'}",
        ),
        SensorStatus(
            "Calibrated spatial observations",
            "ACCEPTED" if evidence.accepted_observation_count else "NO POSITION UPDATE",
            f"{evidence.accepted_observation_count} accepted; {evidence.rejected_observation_count} rejected",
        ),
    )
    warnings = list(evidence.notes)
    warnings.extend(
        f"{check.name}: {check.detail}"
        for check in scene.checks if not check.passed
    )
    if not warnings:
        warnings.append("No quality-gate warnings in this snapshot.")
    return FusedSpatialScene(
        scene=scene, evidence=evidence, sensor_status=statuses,
        warnings=tuple(dict.fromkeys(warnings)),
    )
