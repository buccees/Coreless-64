"""Blueprint registration and deterministic model-frame spatial primitives.

The first milestone accepts already-extracted feature records. PDF/CAD/3D-file
parsers and live sensor adapters can feed this boundary later; this module does
not pretend to extract geometry from arbitrary documents.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
import json
from math import isfinite, sqrt
from typing import Iterable, Mapping, Sequence


_UNIT_TO_METERS = {
    "m": 1.0,
    "meter": 1.0,
    "meters": 1.0,
    "cm": 0.01,
    "mm": 0.001,
    "ft": 0.3048,
    "feet": 0.3048,
    "in": 0.0254,
    "inch": 0.0254,
    "inches": 0.0254,
}


class PoseState(str, Enum):
    UNINITIALIZED = "UNINITIALIZED"
    CALIBRATING = "CALIBRATING"
    TRACKING = "TRACKING"
    DEGRADED = "DEGRADED"
    LOST = "LOST"


@dataclass(frozen=True)
class ModelFeature:
    feature_id: str
    label: str
    position_m: tuple[float, float, float]
    feature_type: str = "anchor"
    level: str | None = None
    zone: str | None = None

    def __post_init__(self) -> None:
        if not self.feature_id.strip() or not self.label.strip():
            raise ValueError("feature_id and label must not be empty")
        _validate_vector(self.position_m, "feature position")


@dataclass(frozen=True)
class BlueprintModel:
    model_id: str
    revision: str
    frame_id: str
    source_units: str
    features: tuple[ModelFeature, ...]
    source_sha256: str
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.model_id.strip() or not self.revision.strip() or not self.frame_id.strip():
            raise ValueError("model_id, revision, and frame_id must not be empty")
        if not self.features:
            raise ValueError("blueprint must contain at least one feature")
        ids = [feature.feature_id for feature in self.features]
        if len(ids) != len(set(ids)):
            raise ValueError("blueprint feature IDs must be unique")


@dataclass(frozen=True)
class CoordinateTransform:
    """A scaled rigid transform from one named frame into another.

    Rotation is a row-major 3x3 matrix. Translation is expressed in target-frame
    units. Scale is applied to the source point before rotation.
    """
    source_frame: str
    target_frame: str
    rotation: tuple[float, ...] = (
        1.0, 0.0, 0.0,
        0.0, 1.0, 0.0,
        0.0, 0.0, 1.0,
    )
    translation: tuple[float, float, float] = (0.0, 0.0, 0.0)
    scale: float = 1.0
    provenance: str = "unspecified"

    def __post_init__(self) -> None:
        if not self.source_frame.strip() or not self.target_frame.strip():
            raise ValueError("transform frame IDs must not be empty")
        if len(self.rotation) != 9 or not all(isfinite(v) for v in self.rotation):
            raise ValueError("rotation must contain nine finite values")
        _validate_vector(self.translation, "transform translation")
        if not isfinite(self.scale) or self.scale <= 0:
            raise ValueError("transform scale must be finite and positive")
        # Reject matrices that are clearly not rotations; tolerates normal rounding.
        rows = (self.rotation[0:3], self.rotation[3:6], self.rotation[6:9])
        for i, row in enumerate(rows):
            if abs(sum(v * v for v in row) - 1.0) > 1e-5:
                raise ValueError("rotation rows must have unit length")
            for other in rows[i + 1:]:
                if abs(sum(a * b for a, b in zip(row, other))) > 1e-5:
                    raise ValueError("rotation rows must be orthogonal")

    def apply(self, point: Sequence[float], *, source_frame: str) -> tuple[float, float, float]:
        if source_frame != self.source_frame:
            raise ValueError(
                f"transform expects frame {self.source_frame!r}, got {source_frame!r}"
            )
        x, y, z = _validate_vector(point, "point")
        x, y, z = x * self.scale, y * self.scale, z * self.scale
        r = self.rotation
        return (
            r[0] * x + r[1] * y + r[2] * z + self.translation[0],
            r[3] * x + r[4] * y + r[5] * z + self.translation[1],
            r[6] * x + r[7] * y + r[8] * z + self.translation[2],
        )


@dataclass(frozen=True)
class PoseEstimate:
    model_id: str
    model_revision: str
    frame_id: str
    position_m: tuple[float, float, float] | None
    state: PoseState
    uncertainty_m: float | None
    observation_timestamp_ns: int | None
    provenance: tuple[str, ...] = ()
    reason: str | None = None

    def __post_init__(self) -> None:
        if not self.model_id or not self.model_revision or not self.frame_id:
            raise ValueError("pose must identify its model, revision, and frame")
        if self.position_m is not None:
            _validate_vector(self.position_m, "pose position")
        if self.uncertainty_m is not None and (
            not isfinite(self.uncertainty_m) or self.uncertainty_m < 0
        ):
            raise ValueError("uncertainty_m must be finite and non-negative")
        if self.observation_timestamp_ns is not None and self.observation_timestamp_ns < 0:
            raise ValueError("observation timestamp must be non-negative")
        if self.state == PoseState.TRACKING and (
            self.position_m is None or self.uncertainty_m is None
        ):
            raise ValueError("TRACKING pose requires position and uncertainty")


def _validate_vector(values: Sequence[float], label: str) -> tuple[float, float, float]:
    if len(values) != 3:
        raise ValueError(f"{label} must contain exactly three values")
    vector = tuple(float(value) for value in values)
    if not all(isfinite(value) for value in vector):
        raise ValueError(f"{label} values must be finite")
    return vector  # type: ignore[return-value]


def register_blueprint(
    model_id: str,
    revision: str,
    *,
    frame_id: str,
    units: str,
    features: Iterable[Mapping[str, object]],
    metadata: Mapping[str, object] | None = None,
) -> BlueprintModel:
    """Validate extracted blueprint features and normalize coordinates to meters."""
    normalized_units = units.strip().lower()
    try:
        unit_scale = _UNIT_TO_METERS[normalized_units]
    except KeyError as exc:
        raise ValueError(f"unsupported blueprint units: {units!r}") from exc

    parsed: list[ModelFeature] = []
    for item in features:
        feature_id = item.get("feature_id")
        label = item.get("label")
        position = item.get("position")
        if not isinstance(feature_id, str) or not isinstance(label, str):
            raise ValueError("each feature requires string feature_id and label")
        if not isinstance(position, (list, tuple)):
            raise ValueError(f"feature {feature_id!r} requires a 3D position")
        x, y, z = _validate_vector(position, f"feature {feature_id!r} position")
        level = item.get("level")
        zone = item.get("zone")
        feature_type = item.get("feature_type", "anchor")
        if not isinstance(feature_type, str):
            raise ValueError("feature_type must be a string")
        if level is not None and not isinstance(level, str):
            raise ValueError("level must be a string or None")
        if zone is not None and not isinstance(zone, str):
            raise ValueError("zone must be a string or None")
        parsed.append(ModelFeature(
            feature_id=feature_id,
            label=label,
            position_m=(x * unit_scale, y * unit_scale, z * unit_scale),
            feature_type=feature_type,
            level=level,
            zone=zone,
        ))

    canonical = {
        "model_id": model_id,
        "revision": revision,
        "frame_id": frame_id,
        "units": normalized_units,
        "features": [
            {
                "feature_id": f.feature_id,
                "label": f.label,
                "position_m": f.position_m,
                "feature_type": f.feature_type,
                "level": f.level,
                "zone": f.zone,
            }
            for f in parsed
        ],
    }
    digest = sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return BlueprintModel(
        model_id=model_id,
        revision=revision,
        frame_id=frame_id,
        source_units=normalized_units,
        features=tuple(parsed),
        source_sha256=digest,
        metadata=dict(metadata or {}),
    )


def nearest_feature(
    model: BlueprintModel,
    position_m: Sequence[float],
    *,
    max_distance_m: float | None = None,
) -> tuple[ModelFeature, float] | None:
    """Return the nearest registered feature and distance, or None beyond range."""
    point = _validate_vector(position_m, "query position")
    if max_distance_m is not None and (
        not isfinite(max_distance_m) or max_distance_m < 0
    ):
        raise ValueError("max_distance_m must be finite and non-negative")
    nearest: tuple[ModelFeature, float] | None = None
    for feature in model.features:
        distance = sqrt(sum((a - b) ** 2 for a, b in zip(point, feature.position_m)))
        if nearest is None or distance < nearest[1]:
            nearest = (feature, distance)
    if nearest is None or (max_distance_m is not None and nearest[1] > max_distance_m):
        return None
    return nearest
