"""Deterministic sensor-observation fusion for registered blueprint models.

Adapters must transform observations into the active model frame before they
reach this estimator. Raw geodetic coordinates are never treated as model
coordinates implicitly.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, sqrt
from typing import Iterable, Sequence

from .blueprint import BlueprintModel, PoseEstimate, PoseState, _validate_vector


@dataclass(frozen=True)
class SpatialObservation:
    observation_id: str
    source_id: str
    model_id: str
    model_revision: str
    frame_id: str
    timestamp_ns: int
    position_m: tuple[float, float, float]
    uncertainty_m: float
    provenance: str

    def __post_init__(self) -> None:
        if not all((self.observation_id, self.source_id, self.model_id,
                    self.model_revision, self.frame_id, self.provenance)):
            raise ValueError("observation identity, frame, and provenance are required")
        if self.timestamp_ns < 0:
            raise ValueError("observation timestamp must be non-negative")
        _validate_vector(self.position_m, "observation position")
        if not isfinite(self.uncertainty_m) or self.uncertainty_m <= 0:
            raise ValueError("observation uncertainty must be finite and positive")


class FakeObservationProvider:
    """Small deterministic provider for tests and development without hardware."""

    def __init__(self, observations: Iterable[SpatialObservation] = ()) -> None:
        self._observations = tuple(observations)

    def read(self) -> tuple[SpatialObservation, ...]:
        return self._observations


class PoseEstimator:
    """Fuse only fresh, calibrated observations in the registered model frame."""

    def update(
        self,
        model: BlueprintModel,
        observations: Sequence[SpatialObservation],
        *,
        now_ns: int,
        max_age_ns: int = 2_000_000_000,
        max_uncertainty_m: float = 5.0,
        max_disagreement_m: float = 2.0,
    ) -> PoseEstimate:
        if now_ns < 0 or max_age_ns < 0:
            raise ValueError("time values must be non-negative")
        if not isfinite(max_uncertainty_m) or max_uncertainty_m <= 0:
            raise ValueError("max_uncertainty_m must be finite and positive")
        if not isfinite(max_disagreement_m) or max_disagreement_m < 0:
            raise ValueError("max_disagreement_m must be finite and non-negative")

        compatible: list[SpatialObservation] = []
        saw_stale = False
        saw_incompatible = False
        for item in observations:
            if (
                item.model_id != model.model_id
                or item.model_revision != model.revision
                or item.frame_id != model.frame_id
                or item.timestamp_ns > now_ns
            ):
                saw_incompatible = True
                continue
            if now_ns - item.timestamp_ns > max_age_ns:
                saw_stale = True
                continue
            compatible.append(item)

        if not compatible:
            reason = (
                "all observations are stale" if saw_stale and not saw_incompatible
                else "no fresh observation aligned to the active model revision and frame"
            )
            return PoseEstimate(
                model_id=model.model_id,
                model_revision=model.revision,
                frame_id=model.frame_id,
                position_m=None,
                state=PoseState.LOST,
                uncertainty_m=None,
                observation_timestamp_ns=None,
                reason=reason,
            )

        weights = [1.0 / (item.uncertainty_m ** 2) for item in compatible]
        total_weight = sum(weights)
        position = tuple(
            sum(weight * item.position_m[axis] for weight, item in zip(weights, compatible))
            / total_weight
            for axis in range(3)
        )
        residuals = [
            sqrt(sum((item.position_m[axis] - position[axis]) ** 2 for axis in range(3)))
            for item in compatible
        ]
        weighted_spread = sum(
            weight * residual * residual
            for weight, residual in zip(weights, residuals)
        ) / total_weight
        uncertainty = sqrt((1.0 / total_weight) + weighted_spread)
        distinct_sources = {item.source_id for item in compatible}
        consistent = max(residuals, default=0.0) <= max_disagreement_m
        state = (
            PoseState.TRACKING
            if len(distinct_sources) >= 2 and consistent and uncertainty <= max_uncertainty_m
            else PoseState.DEGRADED
        )
        return PoseEstimate(
            model_id=model.model_id,
            model_revision=model.revision,
            frame_id=model.frame_id,
            position_m=position,
            state=state,
            uncertainty_m=uncertainty,
            observation_timestamp_ns=max(item.timestamp_ns for item in compatible),
            provenance=tuple(item.observation_id for item in compatible),
            reason=None if state == PoseState.TRACKING else (
                "single-source, inconsistent, or high-uncertainty observations"
            ),
        )
