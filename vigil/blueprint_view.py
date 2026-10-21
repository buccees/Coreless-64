"""Render-ready deterministic geometry projection for blueprint viewers.

This module converts registered meter-based features and a compatible pose into
plain data for a UI/3D renderer. It does not parse source CAD/PDF/mesh files or
own a graphics engine.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Sequence

from .blueprint import BlueprintModel, ModelFeature, PoseEstimate, _validate_vector


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
class BlueprintView:
    model_id: str
    revision: str
    frame_id: str
    source_sha256: str
    selected_level: str | None
    bounds_m: tuple[AxisBounds, AxisBounds, AxisBounds]
    features: tuple[FeatureProjection, ...]
    pose: PoseProjection | None


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


def build_blueprint_view(
    model: BlueprintModel,
    pose: PoseEstimate | None = None,
    *,
    selected_level: str | None = None,
) -> BlueprintView:
    """Build stable, render-ready feature coordinates and an optional pose overlay.

    Coordinates stay in meters in the source model frame. Normalized positions
    are relative to the visible feature bounds; a pose outside those bounds is
    deliberately allowed outside [0, 1] so renderers can show it off-plan.
    """
    if selected_level is not None and not selected_level.strip():
        raise ValueError("selected_level must not be empty")
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

    return BlueprintView(
        model_id=model.model_id,
        revision=model.revision,
        frame_id=model.frame_id,
        source_sha256=model.source_sha256,
        selected_level=selected_level,
        bounds_m=bounds,
        features=projected,
        pose=pose_projection,
    )
