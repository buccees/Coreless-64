"""Research-grade feature extraction primitives for 2.4 GHz Wi-Fi CSI sensing.

Consumes calibrated complex CSI samples from a compatible radio driver. This is
not a radio driver, range estimator, or object detector: features are evidence
for the downstream tracker and must be validated against real hardware.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import atan2, isfinite, pi, sin, cos, sqrt
from statistics import median
from typing import Sequence


@dataclass(frozen=True)
class CsiFeatures:
    subcarrier_count: int
    amplitude_rms_delta: float
    phase_rms_delta_rad: float
    amplitude_coefficient_of_variation: float
    motion_evidence: float


@dataclass(frozen=True)
class MotionState:
    smoothed_evidence: float
    active: bool
    consecutive_high: int
    consecutive_low: int


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
    """Compare aligned CSI vectors; score is evidence, not probability or range.

    Samples must share radio, antenna pair, subcarrier ordering and calibration.
    A median-centered robust aggregate limits isolated subcarrier spikes.
    """
    _validate_vector(baseline, "baseline")
    _validate_vector(current, "current")
    if len(baseline) != len(current):
        raise ValueError("baseline and current CSI vectors must be aligned")

    amp_deltas: list[float] = []
    phase_deltas: list[float] = []
    baseline_amps = [abs(v) for v in baseline]
    for before, after in zip(baseline, current):
        a0, a1 = abs(before), abs(after)
        amp_deltas.append((a1 - a0) / a0)
        phase = atan2(after.imag, after.real) - atan2(before.imag, before.real)
        phase_deltas.append(atan2(sin(phase), cos(phase)))

    amp_median = median(amp_deltas)
    phase_median = median(phase_deltas)
    amp_robust = median([abs(v - amp_median) for v in amp_deltas]) * 1.4826 + abs(amp_median)
    phase_robust = median([abs(v - phase_median) for v in phase_deltas]) * 1.4826 + abs(phase_median)
    amplitude_rms = sqrt(sum(v * v for v in amp_deltas) / len(amp_deltas))
    phase_rms = sqrt(sum(v * v for v in phase_deltas) / len(phase_deltas))
    mean_amp = sum(baseline_amps) / len(baseline_amps)
    variance = sum((v - mean_amp) ** 2 for v in baseline_amps) / len(baseline_amps)
    cv = sqrt(variance) / mean_amp if mean_amp > 0 else 0.0

    # Initial heuristic only; hardware/environment calibration is required.
    amplitude_signal = min(1.0, max(amp_robust, 0.25 * amplitude_rms))
    phase_signal = min(1.0, max(phase_robust, 0.25 * phase_rms) / pi)
    motion = min(1.0, 0.65 * amplitude_signal + 0.35 * phase_signal)
    return CsiFeatures(len(baseline), amplitude_rms, phase_rms, cv, motion)


class MotionEvidenceFilter:
    """EWMA smoothing plus hysteresis to stabilize CSI motion evidence.

    Enters active state after enter_samples consecutive samples above the high
    threshold; exits after exit_samples consecutive samples below the low
    threshold. Thresholds are heuristic until calibrated with labeled recordings.
    """

    def __init__(
        self,
        *,
        alpha: float = 0.35,
        high_threshold: float = 0.28,
        low_threshold: float = 0.16,
        enter_samples: int = 3,
        exit_samples: int = 5,
    ) -> None:
        if not isfinite(alpha) or not 0 < alpha <= 1:
            raise ValueError("alpha must be in (0, 1]")
        if not (isfinite(low_threshold) and isfinite(high_threshold)
                and 0 <= low_threshold < high_threshold <= 1):
            raise ValueError("thresholds must satisfy 0 <= low < high <= 1")
        if isinstance(enter_samples, bool) or not isinstance(enter_samples, int) or enter_samples < 1:
            raise ValueError("enter_samples must be a positive integer")
        if isinstance(exit_samples, bool) or not isinstance(exit_samples, int) or exit_samples < 1:
            raise ValueError("exit_samples must be a positive integer")
        self.alpha = alpha
        self.high_threshold = high_threshold
        self.low_threshold = low_threshold
        self.enter_samples = enter_samples
        self.exit_samples = exit_samples
        self._smoothed: float | None = None
        self._active = False
        self._high = 0
        self._low = 0

    def update(self, evidence: float) -> MotionState:
        """Consume one finite [0, 1] score and return the updated state."""
        if not isfinite(evidence) or not 0 <= evidence <= 1:
            raise ValueError("evidence must be finite and in [0, 1]")
        if self._smoothed is None:
            self._smoothed = evidence
        else:
            self._smoothed = self.alpha * evidence + (1 - self.alpha) * self._smoothed

        if not self._active:
            self._high = self._high + 1 if self._smoothed >= self.high_threshold else 0
            self._low = 0
            if self._high >= self.enter_samples:
                self._active = True
                self._high = 0
        else:
            self._low = self._low + 1 if self._smoothed <= self.low_threshold else 0
            self._high = 0
            if self._low >= self.exit_samples:
                self._active = False
                self._low = 0
        return MotionState(self._smoothed, self._active, self._high, self._low)
