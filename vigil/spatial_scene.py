"""Quality-gated spatial scene assembly for VIGIL's finishing-move sequence.

The dramatic "FATALITY" banner is earned only when deterministic spatial checks
pass. This module does not authorize physical actions or replace Coreless policy.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from math import isfinite
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
    stale_track_count: int
    conflict_count: int
    usable_track_count: int
    uncertain_track_count: int
    unknown_uncertainty_track_count: int
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
    max_ir_age_ns: int = 2_000_000_000,
    max_pose_uncertainty_m: float = 2.0,
    max_track_uncertainty_m: float = 1.0,
    require_conflict_free_tracks: bool = True,
) -> SpatialScene:
    """Build a render-ready scene and explain exactly why it is or isn't ready."""
    if now_ns < 0 or max_pose_age_ns < 0 or max_object_age_ns < 0 or max_ir_age_ns < 0:
        raise ValueError("timestamps and age limits must be non-negative")
    if max_pose_uncertainty_m <= 0:
        raise ValueError("max_pose_uncertainty_m must be positive")
    if not isinstance(max_track_uncertainty_m, (int, float)) or isinstance(max_track_uncertainty_m, bool) or not isfinite(max_track_uncertainty_m) or max_track_uncertainty_m <= 0:
        raise ValueError("max_track_uncertainty_m must be finite and positive")

    checks: list[SceneCheck] = []
    aligned_pose = False
    pose_fresh = False
    pose_precise = False
    pose_state_usable = False
    valid_tracks: list[ObjectTrack] = []
    display_tracks: list[ObjectTrack] = []
    stale_track_count = 0
    valid_ir_levels: set[str] = set()
    aligned_ir_count = 0
    stale_ir_count = 0
    future_ir_count = 0
    mismatched_ir_count = 0
    view = None

    checks.append(SceneCheck("blueprint_registered", model is not None,
                             "active blueprint available" if model else "no active blueprint"))
    if model is not None:
        for track in object_tracks:
            if (track.model_id, track.model_revision, track.frame_id) != (
                model.model_id, model.revision, model.frame_id
            ) or track.last_seen_ns > now_ns:
                continue
            age_ns = now_ns - track.last_seen_ns
            if age_ns <= max_object_age_ns:
                current = replace(track, presence_state="TRACKING")
                valid_tracks.append(current)
                display_tracks.append(current)
            else:
                # Preserve the last known map marker, but keep it out of all
                # current-evidence counts and readiness checks.
                display_tracks.append(replace(track, presence_state="STALE"))
                stale_track_count += 1
        for item in infrared_maps:
            if (item.model_id, item.model_revision, item.frame_id) != (
                model.model_id, model.revision, model.frame_id
            ):
                mismatched_ir_count += 1
                continue
            if not item.level_id.strip():
                mismatched_ir_count += 1
                continue
            age_ns = now_ns - item.timestamp_ns
            if age_ns < 0:
                future_ir_count += 1
                continue
            if age_ns > max_ir_age_ns:
                stale_ir_count += 1
                continue
            valid_ir_levels.add(item.level_id)
            aligned_ir_count += 1
        try:
            view = build_blueprint_view(
                model, pose, selected_level=selected_level, object_tracks=display_tracks
            )
        except (ValueError, TypeError):
            view = None
    checks.append(SceneCheck("blueprint_view_built", view is not None,
                             "geometry and overlays projected" if view else "view projection failed"))
    if model is None:
        level_valid = False
        level_detail = "no active blueprint"
    else:
        modeled_levels = {feature.level for feature in model.features if feature.level is not None}
        level_valid = (selected_level in modeled_levels) if modeled_levels else (selected_level is None)
        level_detail = (
            f"selected floor {selected_level} exists in model"
            if level_valid and selected_level is not None
            else "model has no floor labels; floor selection not required"
            if level_valid
            else f"selected floor {selected_level!r} is missing or unset"
        )
    checks.append(SceneCheck("active_floor_selected", level_valid, level_detail))

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
    unknown_uncertainty_track_count = sum(
        not isinstance(track.uncertainty_m, (int, float))
        or isinstance(track.uncertainty_m, bool)
        or not isfinite(track.uncertainty_m)
        or track.uncertainty_m <= 0
        for track in valid_tracks
    )
    uncertain_track_count = sum(
        isinstance(track.uncertainty_m, (int, float))
        and not isinstance(track.uncertainty_m, bool)
        and __import__("math").isfinite(track.uncertainty_m)
        and track.uncertainty_m > max_track_uncertainty_m
        for track in valid_tracks
    )
    usable_track_count = sum(
        not track.conflict
        and isinstance(track.uncertainty_m, (int, float))
        and not isinstance(track.uncertainty_m, bool)
        and __import__("math").isfinite(track.uncertainty_m)
        and 0 < track.uncertainty_m <= max_track_uncertainty_m
        for track in valid_tracks
    )
    tracks_clear = conflict_count == 0 or not require_conflict_free_tracks
    checks.append(SceneCheck("object_tracks_consistent", tracks_clear,
                             "no active track conflicts" if conflict_count == 0 else f"{conflict_count} active track conflict(s)"))
    checks.append(SceneCheck(
        "object_track_uncertainty_known", unknown_uncertainty_track_count == 0,
        "uncertainty is known and valid for every active track"
        if unknown_uncertainty_track_count == 0
        else f"{unknown_uncertainty_track_count} active track(s) have missing or invalid uncertainty",
    ))
    checks.append(SceneCheck(
        "object_track_quality", True,
        f"{usable_track_count} usable track(s); {uncertain_track_count} uncertain track(s) above "
        f"{max_track_uncertainty_m:.2f} m; {conflict_count} conflicted track(s). "
        "Uncertain tracks remain visible but must not be treated as precise fixes.",
    ))
    failed_calibration_count = sum(track.calibration_status == "failed" for track in valid_tracks)
    unverified_calibration_count = sum(track.calibration_status == "unverified" for track in valid_tracks)
    unknown_lineage_count = sum(not track.lineage_declared for track in valid_tracks)
    checks.append(SceneCheck(
        "track_calibration_valid", failed_calibration_count == 0,
        "no active track uses failed calibration"
        if failed_calibration_count == 0
        else f"{failed_calibration_count} active track(s) depend on failed calibration; scene readiness blocked",
    ))
    checks.append(SceneCheck(
        "track_calibration_verified", True,
        "all active track calibrations explicitly verified"
        if unverified_calibration_count == 0
        else f"WARNING: {unverified_calibration_count} active track(s) have unverified calibration; software metadata is not physical validation",
    ))
    checks.append(SceneCheck(
        "source_lineage_declared", True,
        "all active tracks declare source lineage"
        if unknown_lineage_count == 0
        else f"WARNING: {unknown_lineage_count} active track(s) have undeclared source lineage; sensor IDs alone do not prove independent hardware",
    ))
    # Infrared is optional for readiness, but only fresh, time-aligned maps are exposed.
    ir_detail = (
        f"{aligned_ir_count} fresh aligned map(s) across {len(valid_ir_levels)} floor(s)"
        if aligned_ir_count else "no fresh aligned IR overlay; scene remains eligible"
    )
    ir_rejections = []
    if stale_ir_count:
        ir_rejections.append(f"{stale_ir_count} stale")
    if future_ir_count:
        ir_rejections.append(f"{future_ir_count} future-dated")
    if mismatched_ir_count:
        ir_rejections.append(f"{mismatched_ir_count} frame/revision/floor-invalid")
    if ir_rejections:
        ir_detail += "; excluded " + ", ".join(ir_rejections)
    checks.append(SceneCheck("infrared_overlay_optional", True, ir_detail))

    ready = all(check.passed for check in checks if check.name != "infrared_overlay_optional")
    return SpatialScene(
        model_id=model.model_id if model else None,
        model_revision=model.revision if model else None,
        frame_id=model.frame_id if model else None,
        selected_level=selected_level,
        view=view,
        infrared_levels=tuple(sorted(valid_ir_levels)),
        object_count=len(valid_tracks),
        stale_track_count=stale_track_count,
        conflict_count=conflict_count,
        usable_track_count=usable_track_count,
        uncertain_track_count=uncertain_track_count,
        unknown_uncertainty_track_count=unknown_uncertainty_track_count,
        checks=tuple(checks),
        finishing_move_ready=ready,
        banner="FATALITY // SPATIAL SCENE LOCKED" if ready else "FATALITY DENIED // VALIDATION INCOMPLETE",
    )
