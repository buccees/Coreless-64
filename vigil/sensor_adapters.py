"""Sensor measurement adapters for VIGIL's shared building coordinate frame.

These adapters consume calibrated measurements supplied by hardware drivers; they
are not hardware drivers and do not infer range from raw RSSI, phase, or audio.
RF time-of-flight and acoustic time-of-flight use different propagation speeds.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, sqrt
from typing import Sequence

from .blueprint import BlueprintModel
from .object_tracking import ObjectObservation, TrackingModality

SPEED_OF_LIGHT_MPS = 299_792_458.0
DEFAULT_SOUND_SPEED_MPS = 343.0


@dataclass(frozen=True)
class RangeMeasurement:
    sensor_id: str
    object_id: str
    model_id: str
    model_revision: str
    frame_id: str
    timestamp_ns: int
    anchor_position_m: tuple[float, float, float]
    range_m: float
    uncertainty_m: float
    modality: TrackingModality
    provenance: str
    # Optional lineage for feeds known to share a receiver or upstream processing.
    independence_group: str | None = None
    # verified / unverified / failed; unverified is retained as a warning, failed is rejected.
    calibration_status: str = "unverified"
    calibration_id: str | None = None

    def __post_init__(self) -> None:
        if not all(isinstance(v, str) and v.strip() for v in (
            self.sensor_id, self.object_id, self.model_id, self.model_revision,
            self.frame_id, self.provenance,
        )):
            raise ValueError("sensor, object, model, frame, and provenance IDs are required")
        if isinstance(self.timestamp_ns, bool) or not isinstance(self.timestamp_ns, int) or self.timestamp_ns < 0:
            raise ValueError("timestamp_ns must be a non-negative integer")
        if len(self.anchor_position_m) != 3 or not all(isfinite(v) for v in self.anchor_position_m):
            raise ValueError("anchor position must contain three finite coordinates")
        if not isfinite(self.range_m) or self.range_m <= 0:
            raise ValueError("range_m must be finite and positive")
        if not isfinite(self.uncertainty_m) or self.uncertainty_m <= 0:
            raise ValueError("uncertainty_m must be finite and positive")
        if self.modality not in (TrackingModality.RF_2_4_GHZ, TrackingModality.ACOUSTIC_SONAR):
            raise ValueError("range modality must be RF 2.4 GHz or acoustic sonar")
        if self.independence_group is not None and not self.independence_group.strip():
            raise ValueError("independence_group must be non-empty when provided")
        if self.calibration_status not in ("verified", "unverified", "failed"):
            raise ValueError("calibration_status must be verified, unverified, or failed")
        if self.calibration_id is not None and not self.calibration_id.strip():
            raise ValueError("calibration_id must be non-empty when provided")


def rf_tof_range_m(round_trip_seconds: float) -> float:
    """Convert calibrated RF round-trip time to range; requires turnaround-delay correction."""
    if not isfinite(round_trip_seconds) or round_trip_seconds <= 0:
        raise ValueError("round-trip time must be finite and positive")
    return SPEED_OF_LIGHT_MPS * round_trip_seconds / 2.0


def acoustic_tof_range_m(
    round_trip_seconds: float, *, sound_speed_mps: float = DEFAULT_SOUND_SPEED_MPS
) -> float:
    """Convert acoustic echo round-trip time to range using a supplied sound speed."""
    if not isfinite(round_trip_seconds) or round_trip_seconds <= 0:
        raise ValueError("round-trip time must be finite and positive")
    if not isfinite(sound_speed_mps) or sound_speed_mps <= 0:
        raise ValueError("sound speed must be finite and positive")
    return sound_speed_mps * round_trip_seconds / 2.0


def _solve_linear(matrix: list[list[float]], values: list[float]) -> list[float]:
    """Small Gaussian-elimination solver with pivoting; raises on degenerate geometry."""
    n = len(values)
    augmented = [row[:] + [value] for row, value in zip(matrix, values)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda row: abs(augmented[row][col]))
        if abs(augmented[pivot][col]) < 1e-10:
            raise ValueError("range anchors are geometrically degenerate")
        augmented[col], augmented[pivot] = augmented[pivot], augmented[col]
        divisor = augmented[col][col]
        augmented[col] = [v / divisor for v in augmented[col]]
        for row in range(n):
            if row == col:
                continue
            factor = augmented[row][col]
            augmented[row] = [
                a - factor * b for a, b in zip(augmented[row], augmented[col])
            ]
    return [augmented[i][-1] for i in range(n)]


def trilaterate_3d(measurements: Sequence[RangeMeasurement]) -> tuple[tuple[float, float, float], float]:
    """Solve a 3D position from at least four independent range anchors.

    Returns (position, conservative RMS range residual). The linearized solver is
    intentionally deterministic and rejects singular layouts; production ranging
    should add robust nonlinear refinement/outlier rejection and calibration.
    """
    if len(measurements) < 4:
        raise ValueError("3D trilateration requires at least four range measurements")
    first = measurements[0]
    if any(item.calibration_status == "failed" for item in measurements):
        raise ValueError("range measurements with failed calibration cannot be used for positioning")
    for item in measurements:
        if (item.model_id, item.model_revision, item.frame_id, item.object_id) != (
            first.model_id, first.model_revision, first.frame_id, first.object_id
        ):
            raise ValueError("all ranges must share object, model revision, and coordinate frame")
        if item.timestamp_ns != first.timestamp_ns:
            raise ValueError("all ranges must be from the same measurement epoch")
    p0 = first.anchor_position_m
    r0 = first.range_m
    rows: list[list[float]] = []
    rhs: list[float] = []
    for item in measurements[1:]:
        p = item.anchor_position_m
        rows.append([2 * (p[i] - p0[i]) for i in range(3)])
        rhs.append(
            sum(v * v for v in p) - sum(v * v for v in p0)
            + r0 * r0 - item.range_m * item.range_m
        )
    # Solve least squares via normal equations; multiple anchors can overdetermine.
    normal = [[sum(row[i] * row[j] for row in rows) for j in range(3)] for i in range(3)]
    normal_rhs = [sum(row[i] * value for row, value in zip(rows, rhs)) for i in range(3)]
    position_list = _solve_linear(normal, normal_rhs)
    position = (position_list[0], position_list[1], position_list[2])
    residuals = [
        sqrt(sum((position[i] - item.anchor_position_m[i]) ** 2 for i in range(3))) - item.range_m
        for item in measurements
    ]
    rms = sqrt(sum(r * r for r in residuals) / len(residuals))
    return position, rms


def to_object_observation(
    model: BlueprintModel,
    measurements: Sequence[RangeMeasurement],
    *,
    max_rms_residual_m: float = 1.5,
) -> ObjectObservation:
    """Adapt one consistent range epoch into the existing object tracker contract."""
    if not measurements:
        raise ValueError("at least four range measurements are required")
    if not isfinite(max_rms_residual_m) or max_rms_residual_m <= 0:
        raise ValueError("max_rms_residual_m must be finite and positive")
    first = measurements[0]
    if (first.model_id, first.model_revision, first.frame_id) != (
        model.model_id, model.revision, model.frame_id
    ):
        raise ValueError("range measurement model/revision/frame does not match active blueprint")
    position, residual = trilaterate_3d(measurements)
    if residual > max_rms_residual_m:
        raise ValueError("range geometry residual exceeds configured safety threshold")
    modality = first.modality
    if any(item.modality != modality for item in measurements):
        # Do not pretend the ranges share a physical propagation model. A fused
        # upstream solver may combine modalities, but that is a separate contract.
        raise ValueError("one trilateration solve must use a single sensing modality")
    groups = sorted({item.independence_group for item in measurements if item.independence_group})
    calibration_ids = sorted({item.calibration_id for item in measurements if item.calibration_id})
    calibration_states = sorted({item.calibration_status for item in measurements})
    provenance = "trilateration:" + ",".join(sorted({item.provenance for item in measurements}))
    if "unverified" in calibration_states:
        provenance += "|calibration=UNVERIFIED"
    if calibration_ids:
        provenance += "|calibration_ids=" + ",".join(calibration_ids)
    # Use a shared token only when every contributing range declares the same lineage.
    independence_group = groups[0] if len(groups) == 1 and all(item.independence_group for item in measurements) else None
    return ObjectObservation(
        object_id=first.object_id,
        sensor_id="+".join(sorted({item.sensor_id for item in measurements})),
        model_id=model.model_id,
        model_revision=model.revision,
        frame_id=model.frame_id,
        timestamp_ns=first.timestamp_ns,
        position_m=position,
        uncertainty_m=max(residual, sqrt(sum(item.uncertainty_m ** 2 for item in measurements) / len(measurements))),
        modality=modality,
        provenance=provenance,
        independence_group=independence_group,
        calibration_status=("failed" if "failed" in calibration_states else "unverified" if "unverified" in calibration_states else "verified"),
        calibration_ids=tuple(calibration_ids),
        lineage_declared=bool(measurements) and all(item.independence_group for item in measurements) and len(groups) == 1,
    )
