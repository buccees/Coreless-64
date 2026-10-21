"""Quality-gated spatial scene assembly for VIGIL's finishing-move sequence.

The dramatic "FATALITY" banner is earned only when deterministic spatial checks
pass. This module does not authorize physical actions or replace Coreless policy.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .blueprint import BlueprintModel, PoseEstimate
from .blueprint_view import BlueprintView, build_blueprint_view
from .infrared_floor_mapping import InfraredFloorMap
from .object_tracking import ObjectTrack


@dataclass(frozen=True)
class SceneCheck:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class SpatialScene:
    model_id: str | None
    model_revision: str | None
    frame_id: str | None
    selected_level: str | None
    view: BlueprintView | None
    infrared_levels: tuple[str, ...]
    object_count: int
    conflict_count: int
    checks: tuple[SceneCheck, ...]
    finishing_move_ready: bool
    banner: str


def assemble_spatial_scene(
    model: BlueprintModel | None,
    pose: PoseEstimate | None,
    object_tracks: Sequence[ObjectTrack] = (),
    infrared_maps: Sequence[InfraredFloorMap] = (),
    *,
    selected_level: str | None,
    now_ns: int,
    max_pose_age_ns: int = 2_000_000_000,
    max_object_age_ns: int = 2_000_000_000,
    max_pose_uncertainty_m: float = 2.0,
    require_conflict_free_tracks: bool = True,
) -> SpatialScene:
    """Build a render-ready scene and explain exactly why it is or isn't ready."""
    if now_ns < 0 or max_pose_age_ns < 0 or max_object_age_ns < 0:
        raise ValueError("timestamps and age limits must be non-negative")
    if max_pose_uncertainty_m <= 0:
        raise ValueError("max_pose_uncertainty_m must be positive")

    checks: list[SceneCheck] = []
    aligned_pose = False
    pose_fresh = False
    pose_precise = False
    pose_state_usable = False
    valid_tracks: list[ObjectTrack] = []
    valid_ir_levels: set[str] = set()
    view = None

    checks.append(SceneCheck("blueprint_registered", model is not None,
                             "active blueprint available" if model else "no active blueprint"))
    if model is not None:
        valid_tracks = [
            track for track in object_tracks
            if (track.model_id, track.model_revision, track.frame_id) ==
               (model.model_id, model.revision, model.frame_id)
            and 0 <= now_ns - track.last_seen_ns <= max_object_age_ns
        ]
        for item in infrared_maps:
            if (item.model_id, item.model_revision, item.frame_id) == (
                model.model_id, model.revision, model.frame_id
            ) and item.level_id.strip():
                valid_ir_levels.add(item.level_id)
        try:
            view = build_blueprint_view(
                model, pose, selected_level=selected_level, object_tracks=valid_tracks
            )
        except (ValueError, TypeError):
            view = None
    checks.append(SceneCheck("blueprint_view_built", view is not None,
                             "geometry and overlays projected" if view else "view projection failed"))

    if model is not None and pose is not None:
        aligned_pose = (pose.model_id, pose.model_revision, pose.frame_id) == (
            model.model_id, model.revision, model.frame_id
        )
        pose_fresh = (
            pose.observation_timestamp_ns is not None
            and 0 <= now_ns - pose.observation_timestamp_ns <= max_pose_age_ns
        )
        pose_state_usable = pose.state.value in ("TRACKING", "DEGRADED")
        pose_precise = (
            pose_state_usable
            and pose.position_m is not None
            and pose.uncertainty_m is not None
            and pose.uncertainty_m <= max_pose_uncertainty_m
        )
    checks.append(SceneCheck("pose_frame_aligned", aligned_pose,
                             "pose matches active model revision and frame" if aligned_pose else "pose absent or frame/revision mismatch"))
    checks.append(SceneCheck("pose_fresh", pose_fresh,
                             "pose timestamp within freshness limit" if pose_fresh else "pose missing, future-dated, or stale"))
    checks.append(SceneCheck("pose_confidence", pose_precise,
                             f"{pose.state.value}; uncertainty within {max_pose_uncertainty_m:.2f} m" if pose_precise and pose is not None else "pose not tracking/degraded, position missing, or uncertainty exceeds limit"))

    conflict_count = sum(track.conflict for track in valid_tracks)
    tracks_clear = conflict_count == 0 or not require_conflict_free_tracks
    checks.append(SceneCheck("object_tracks_consistent", tracks_clear,
                             "no active track conflicts" if conflict_count == 0 else f"{conflict_count} active track conflict(s)"))
    # Infrared is an optional overlay, not a mandatory readiness dependency.
    checks.append(SceneCheck("infrared_overlay_optional", True,
                             f"{len(valid_ir_levels)} calibrated floor overlay(s)" if valid_ir_levels else "no aligned IR overlay; scene remains eligible"))

    ready = all(check.passed for check in checks if check.name != "infrared_overlay_optional")
    return SpatialScene(
        model_id=model.model_id if model else None,
        model_revision=model.revision if model else None,
        frame_id=model.frame_id if model else None,
        selected_level=selected_level,
        view=view,
        infrared_levels=tuple(sorted(valid_ir_levels)),
        object_count=len(valid_tracks),
        conflict_count=conflict_count,
        checks=tuple(checks),
        finishing_move_ready=ready,
        banner="FATALITY // SPATIAL SCENE LOCKED" if ready else "FATALITY DENIED // VALIDATION INCOMPLETE",
    )
