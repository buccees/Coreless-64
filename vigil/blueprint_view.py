"""Render-ready deterministic geometry projection for blueprint viewers.

This module converts registered meter-based features, compatible poses, and
validated object tracks into plain data for a UI/3D renderer. It does not parse
source CAD/PDF/mesh files or own a graphics engine.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Sequence

from .blueprint import BlueprintModel, ModelFeature, PoseEstimate, _validate_vector
from .object_tracking import ObjectTrack


@dataclass(frozen=True)
class AxisBounds:
    minimum: float
    maximum: float

    def normalize(self, value: float) -> float:
        """Map an axis value to [0, 1]; a zero-width axis maps to its center."""
        if not isfinite(value):
            raise ValueError("axis value must be finite")
        span = self.maximum - self.minimum
        if span <= 0:
            return 0.5
        return (value - self.minimum) / span


@dataclass(frozen=True)
class FeatureProjection:
    feature_id: str
    label: str
    feature_type: str
    level: str | None
    zone: str | None
    position_m: tuple[float, float, float]
    normalized_position: tuple[float, float, float]


@dataclass(frozen=True)
class PoseProjection:
    position_m: tuple[float, float, float]
    normalized_position: tuple[float, float, float]
    state: str
    uncertainty_m: float | None
    provenance: tuple[str, ...]


@dataclass(frozen=True)
class ObjectProjection:
    """Renderer-ready track marker; all coordinates remain in the model frame."""

    object_id: str
    association_id: str | None
    position_m: tuple[float, float, float]
    normalized_position: tuple[float, float, float]
    velocity_mps: tuple[float, float, float]
    uncertainty_m: float
    last_seen_ns: int
    sensor_ids: tuple[str, ...]
    modalities: tuple[str, ...]
    provenance: tuple[str, ...]
    conflict: bool
    conflict_reasons: tuple[str, ...]
    conflicting_sensor_ids: tuple[str, ...]
    inferred_level: str | None
    visible_on_selected_level: bool | None


@dataclass(frozen=True)
class BlueprintView:
    model_id: str
    revision: str
    frame_id: str
    source_sha256: str
    selected_level: str | None
    bounds_m: tuple[AxisBounds, AxisBounds, AxisBounds]
    features: tuple[FeatureProjection, ...]
    pose: PoseProjection | None
    objects: tuple[ObjectProjection, ...] = ()


def _bounds(features: Sequence[ModelFeature]) -> tuple[AxisBounds, AxisBounds, AxisBounds]:
    if not features:
        raise ValueError("cannot project a blueprint view with no visible features")
    return tuple(
        AxisBounds(
            min(feature.position_m[axis] for feature in features),
            max(feature.position_m[axis] for feature in features),
        )
        for axis in range(3)
    )  # type: ignore[return-value]


def _normalize(
    point: Sequence[float],
    bounds: tuple[AxisBounds, AxisBounds, AxisBounds],
) -> tuple[float, float, float]:
    values = _validate_vector(point, "projection point")
    return tuple(bounds[axis].normalize(values[axis]) for axis in range(3))  # type: ignore[return-value]


def _floor_elevations(model: BlueprintModel) -> dict[str, float]:
    raw = model.metadata.get("floor_elevations_m")
    if not isinstance(raw, dict):
        return {}
    result: dict[str, float] = {}
    for level, elevation in raw.items():
        if isinstance(level, str) and isinstance(elevation, (int, float)) and not isinstance(elevation, bool) and isfinite(float(elevation)):
            result[level] = float(elevation)
    return result


def build_blueprint_view(
    model: BlueprintModel,
    pose: PoseEstimate | None = None,
    *,
    selected_level: str | None = None,
    object_tracks: Sequence[ObjectTrack] = (),
    floor_elevation_tolerance_m: float = 1.5,
) -> BlueprintView:
    """Build stable feature, pose, and object-marker data for a blueprint renderer.

    Object tracks must match the active model ID, revision, and frame. Their
    coordinates remain in meters in that shared frame. If surveyed floor
    elevations exist in model metadata, tracks are assigned to the nearest floor
    only within the explicit tolerance; otherwise floor visibility is unknown
    rather than guessed from an arbitrary Z coordinate.
    """
    if selected_level is not None and not selected_level.strip():
        raise ValueError("selected_level must not be empty")
    if not isfinite(floor_elevation_tolerance_m) or floor_elevation_tolerance_m <= 0:
        raise ValueError("floor_elevation_tolerance_m must be finite and positive")
    visible = tuple(
        feature for feature in model.features
        if selected_level is None or feature.level is None or feature.level == selected_level
    )
    bounds = _bounds(visible)
    projected = tuple(
        FeatureProjection(
            feature_id=feature.feature_id,
            label=feature.label,
            feature_type=feature.feature_type,
            level=feature.level,
            zone=feature.zone,
            position_m=feature.position_m,
            normalized_position=_normalize(feature.position_m, bounds),
        )
        for feature in visible
    )

    pose_projection = None
    if pose is not None:
        if (pose.model_id, pose.model_revision, pose.frame_id) != (
            model.model_id, model.revision, model.frame_id
        ):
            raise ValueError("pose must match the active blueprint model, revision, and frame")
        if pose.position_m is not None:
            pose_projection = PoseProjection(
                position_m=pose.position_m,
                normalized_position=_normalize(pose.position_m, bounds),
                state=pose.state.value,
                uncertainty_m=pose.uncertainty_m,
                provenance=pose.provenance,
            )

    elevations = _floor_elevations(model)
    object_projections: list[ObjectProjection] = []
    for track in object_tracks:
        if (track.model_id, track.model_revision, track.frame_id) != (
            model.model_id, model.revision, model.frame_id
        ):
            continue
        inferred_level = None
        visible_on_level = None
        if elevations:
            nearest_level, nearest_elevation = min(
                elevations.items(), key=lambda item: abs(track.position_m[2] - item[1])
            )
            if abs(track.position_m[2] - nearest_elevation) <= floor_elevation_tolerance_m:
                inferred_level = nearest_level
            if selected_level is not None:
                visible_on_level = inferred_level == selected_level
        object_projections.append(ObjectProjection(
            object_id=track.object_id,
            association_id=track.association_id,
            position_m=track.position_m,
            normalized_position=_normalize(track.position_m, bounds),
            velocity_mps=track.velocity_mps,
            uncertainty_m=track.uncertainty_m,
            last_seen_ns=track.last_seen_ns,
            sensor_ids=track.sensor_ids,
            modalities=track.modalities,
            provenance=track.provenance,
            conflict=track.conflict,
            conflict_reasons=track.conflict_reasons,
            conflicting_sensor_ids=track.conflicting_sensor_ids,
            inferred_level=inferred_level,
            visible_on_selected_level=visible_on_level,
        ))

    return BlueprintView(
        model_id=model.model_id,
        revision=model.revision,
        frame_id=model.frame_id,
        source_sha256=model.source_sha256,
        selected_level=selected_level,
        bounds_m=bounds,
        features=projected,
        pose=pose_projection,
        objects=tuple(sorted(object_projections, key=lambda item: (item.object_id, item.association_id or ""))),
    )
