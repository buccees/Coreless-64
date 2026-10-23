"""Confidence-aware spatial queries against a registered VIGIL blueprint.

Queries never invent a pose: model/frame identity, freshness, and pose quality
are evaluated before model-relative results are labeled usable. Coordinates are
meters in the blueprint's explicit frame.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite
from typing import Sequence

from .blueprint import BlueprintModel, PoseEstimate, PoseState, _validate_vector, nearest_feature


class SpatialQueryStatus(str, Enum):
    OK = "OK"
    DEGRADED = "DEGRADED"
    NO_FIX = "NO_FIX"
    STALE = "STALE"
    FUTURE_TIMESTAMP = "FUTURE_TIMESTAMP"
    MODEL_MISMATCH = "MODEL_MISMATCH"


@dataclass(frozen=True)
class SpatialQueryResult:
    """Immutable result with enough provenance to avoid treating no-fix as origin."""

    status: SpatialQueryStatus
    model_id: str
    model_revision: str
    frame_id: str
    evaluated_at_ns: int
    observation_timestamp_ns: int | None
    position_m: tuple[float, float, float] | None
    uncertainty_m: float | None
    nearest_feature_id: str | None
    nearest_feature_label: str | None
    nearest_feature_distance_m: float | None
    level: str | None
    zone: str | None
    nearby_feature_ids: tuple[str, ...]
    reason: str | None = None


class SpatialQueryEngine:
    """Evaluate a pose relative to one immutable blueprint revision."""

    def __init__(self, model: BlueprintModel) -> None:
        if not isinstance(model, BlueprintModel):
            raise TypeError("model must be a validated BlueprintModel")
        self.model = model

    def evaluate(
        self,
        pose: PoseEstimate | None,
        *,
        now_ns: int,
        max_age_ns: int = 2_000_000_000,
        max_uncertainty_m: float = 5.0,
        nearby_radius_m: float | None = None,
    ) -> SpatialQueryResult:
        """Return nearest feature/level/zone and nearby features when pose is usable.

        DEGRADED results retain the best available estimate but explicitly label
        it degraded. NO_FIX, STALE, FUTURE_TIMESTAMP, and MODEL_MISMATCH never
        expose derived nearest-feature results.
        """
        if isinstance(now_ns, bool) or not isinstance(now_ns, int) or now_ns < 0:
            raise ValueError("now_ns must be a non-negative integer")
        if isinstance(max_age_ns, bool) or not isinstance(max_age_ns, int) or max_age_ns < 0:
            raise ValueError("max_age_ns must be a non-negative integer")
        if not isfinite(max_uncertainty_m) or max_uncertainty_m < 0:
            raise ValueError("max_uncertainty_m must be finite and non-negative")
        if nearby_radius_m is not None and (
            not isfinite(nearby_radius_m) or nearby_radius_m < 0
        ):
            raise ValueError("nearby_radius_m must be finite and non-negative")

        base = dict(
            model_id=self.model.model_id,
            model_revision=self.model.revision,
            frame_id=self.model.frame_id,
            evaluated_at_ns=now_ns,
            observation_timestamp_ns=pose.observation_timestamp_ns if pose else None,
            position_m=None,
            uncertainty_m=pose.uncertainty_m if pose else None,
            nearest_feature_id=None,
            nearest_feature_label=None,
            nearest_feature_distance_m=None,
            level=None,
            zone=None,
            nearby_feature_ids=(),
        )

        def result(status: SpatialQueryStatus, reason: str) -> SpatialQueryResult:
            return SpatialQueryResult(status=status, reason=reason, **base)

        if pose is None:
            return result(SpatialQueryStatus.NO_FIX, "no pose estimate supplied")
        if (pose.model_id, pose.model_revision, pose.frame_id) != (
            self.model.model_id, self.model.revision, self.model.frame_id
        ):
            return result(SpatialQueryStatus.MODEL_MISMATCH, "pose model, revision, or frame does not match active model")
        if pose.position_m is None or pose.observation_timestamp_ns is None or pose.state in (
            PoseState.UNINITIALIZED, PoseState.CALIBRATING, PoseState.LOST
        ):
            return result(SpatialQueryStatus.NO_FIX, pose.reason or "pose has no usable position fix")
        if pose.observation_timestamp_ns > now_ns:
            return result(SpatialQueryStatus.FUTURE_TIMESTAMP, "pose timestamp is later than query time")
        if now_ns - pose.observation_timestamp_ns > max_age_ns:
            return result(SpatialQueryStatus.STALE, "pose exceeds the configured maximum age")
        # PoseEstimate validates finite uncertainty when present; None remains unknown.
        position = _validate_vector(pose.position_m, "pose position")
        nearest = nearest_feature(self.model, position)
        nearby = tuple(sorted(
            feature.feature_id for feature in self.model.features
            if nearby_radius_m is not None
            and sum((a - b) ** 2 for a, b in zip(position, feature.position_m)) ** 0.5 <= nearby_radius_m
        ))
        if nearest is None:
            return result(SpatialQueryStatus.NO_FIX, "active model has no queryable features")
        feature, distance = nearest
        base.update(
            position_m=position,
            nearest_feature_id=feature.feature_id,
            nearest_feature_label=feature.label,
            nearest_feature_distance_m=distance,
            level=feature.level,
            zone=feature.zone,
            nearby_feature_ids=nearby,
        )
        uncertainty = pose.uncertainty_m
        quality_ok = (
            pose.state == PoseState.TRACKING
            and uncertainty is not None
            and uncertainty <= max_uncertainty_m
        )
        return SpatialQueryResult(
            status=SpatialQueryStatus.OK if quality_ok else SpatialQueryStatus.DEGRADED,
            reason=None if quality_ok else (
                pose.reason or "pose state or uncertainty does not meet the configured quality threshold"
            ),
            **base,
        )
