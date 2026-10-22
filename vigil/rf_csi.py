"""Research-grade feature extraction primitives for 2.4 GHz Wi-Fi CSI sensing.

Consumes calibrated complex CSI samples from a compatible radio driver. This is
not a radio driver, range estimator, or object detector: features are evidence
for the downstream tracker and must be validated against real hardware.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import atan2, isfinite, sqrt
from typing import Sequence


@dataclass(frozen=True)
class CsiFeatures:
    subcarrier_count: int
    amplitude_rms_delta: float
    phase_rms_delta_rad: float
    amplitude_coefficient_of_variation: float
    motion_evidence: float


def _validate_vector(values: Sequence[complex], name: str) -> None:
    if not values:
        raise ValueError(f"{name} must contain at least one subcarrier")
    for value in values:
        if not isfinite(value.real) or not isfinite(value.imag):
            raise ValueError(f"{name} must contain finite complex samples")
        if abs(value) <= 1e-12:
            raise ValueError(f"{name} contains a zero-magnitude CSI sample")


def extract_csi_features(
    baseline: Sequence[complex], current: Sequence[complex]
) -> CsiFeatures:
    """Compare aligned baseline/current CSI vectors without claiming metric range.

    Samples must use the same radio, antenna pair, subcarrier ordering, and
    calibration. Motion evidence is a bounded normalized change score, not a
    probability and not a calibrated distance.
    """
    _validate_vector(baseline, "baseline")
    _validate_vector(current, "current")
    if len(baseline) != len(current):
        raise ValueError("baseline and current CSI vectors must be aligned")

    amp_deltas: list[float] = []
    phase_deltas: list[float] = []
    baseline_amps = [abs(v) for v in baseline]
    current_amps = [abs(v) for v in current]
    for before, after in zip(baseline, current):
        a0, a1 = abs(before), abs(after)
        amp_deltas.append((a1 - a0) / a0)
        phase = atan2(after.imag, after.real) - atan2(before.imag, before.real)
        # Wrap phase delta to [-pi, pi] so crossing the branch cut is not a spike.
        phase_deltas.append(atan2(__import__("math").sin(phase), __import__("math").cos(phase)))

    amplitude_rms = sqrt(sum(v * v for v in amp_deltas) / len(amp_deltas))
    phase_rms = sqrt(sum(v * v for v in phase_deltas) / len(phase_deltas))
    mean_amp = sum(baseline_amps) / len(baseline_amps)
    variance = sum((v - mean_amp) ** 2 for v in baseline_amps) / len(baseline_amps)
    cv = sqrt(variance) / mean_amp if mean_amp > 0 else 0.0
    # Normalize each channel of evidence to [0, 1]; weights are an initial
    # engineering heuristic and should be calibrated per device/environment.
    motion = min(1.0, 0.65 * min(1.0, amplitude_rms) + 0.35 * min(1.0, phase_rms / 3.141592653589793))
    return CsiFeatures(len(baseline), amplitude_rms, phase_rms, cv, motion)
