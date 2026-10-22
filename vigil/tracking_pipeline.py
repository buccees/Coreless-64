"""Calibrated range-to-track orchestration for VIGIL.

CSI motion evidence remains a separate signal: it can indicate change in a radio
channel, but it cannot supply a 3D position. This pipeline only updates tracks
from calibrated, same-epoch range measurements that pass the adapter's checks.
"""
from __future__ import annotations

from collections.abc import Sequence

from .blueprint import BlueprintModel
from .object_tracking import ObjectTrack, ObjectTracker
from .sensor_adapters import RangeMeasurement, to_object_observation


class RangeTrackingPipeline:
    """Convert validated calibrated range epochs into model-frame object tracks."""

    def __init__(
        self,
        model: BlueprintModel,
        *,
        tracker: ObjectTracker | None = None,
        max_rms_residual_m: float = 1.5,
        max_age_ns: int = 1_000_000_000,
    ) -> None:
        if max_age_ns < 0:
            raise ValueError("max_age_ns must be non-negative")
        self.model = model
        self.tracker = tracker or ObjectTracker()
        self.max_rms_residual_m = max_rms_residual_m
        self.max_age_ns = max_age_ns

    def process_epoch(
        self,
        measurements: Sequence[RangeMeasurement],
        *,
        now_ns: int,
    ) -> tuple[ObjectTrack, ...]:
        """Solve one range epoch, then update tracks; invalid epochs are rejected."""
        observation = to_object_observation(
            self.model,
            measurements,
            max_rms_residual_m=self.max_rms_residual_m,
        )
        return self.tracker.update(
            self.model,
            (observation,),
            now_ns=now_ns,
            max_age_ns=self.max_age_ns,
        )
