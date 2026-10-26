"""Deterministic, hardware-independent underwater/sonar simulation feed.

This is a training/game model, not a physical sonar driver. Hidden target state
stays in the simulation; the sensor returns only noisy, authorized contacts.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import hypot, isfinite, atan2, degrees
from typing import Sequence


class SonarMode(str, Enum):
    ACTIVE = "active"
    PASSIVE = "passive"


@dataclass(frozen=True)
class UnderwaterTarget:
    """Simulation-only truth for a submerged target; never expose directly to players."""
    target_id: str
    x_m: float
    y_m: float
    depth_m: float
    acoustic_signature: float = 0.5
    moving: bool = True

    def __post_init__(self) -> None:
        if not self.target_id.strip():
            raise ValueError("target_id is required")
        if not all(isfinite(v) for v in (self.x_m, self.y_m, self.depth_m, self.acoustic_signature)):
            raise ValueError("target state must be finite")
        if self.depth_m < 0 or not 0 <= self.acoustic_signature <= 1:
            raise ValueError("depth must be non-negative and signature must be in [0, 1]")


@dataclass(frozen=True)
class SonarSensor:
    sensor_id: str
    mode: SonarMode
    max_range_m: float
    sensitivity: float = 0.5
    environmental_noise: float = 0.15
    range_uncertainty_fraction: float = 0.08

    def __post_init__(self) -> None:
        if not self.sensor_id.strip():
            raise ValueError("sensor_id is required")
        if not isinstance(self.mode, SonarMode):
            raise ValueError("mode must be SonarMode")
        if not isfinite(self.max_range_m) or self.max_range_m <= 0:
            raise ValueError("max_range_m must be positive and finite")
        for name, value in (("sensitivity", self.sensitivity), ("environmental_noise", self.environmental_noise)):
            if not isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be in [0, 1]")
        if not isfinite(self.range_uncertainty_fraction) or not 0 < self.range_uncertainty_fraction <= 1:
            raise ValueError("range_uncertainty_fraction must be in (0, 1]")


@dataclass(frozen=True)
class SonarContact:
    """Player-authorized sensor result; intentionally contains no true target coordinates or ID."""
    contact_id: str
    sensor_id: str
    mode: SonarMode
    timestamp_ns: int
    estimated_range_m: float
    estimated_bearing_deg: float
    confidence: float
    range_uncertainty_m: float
    classification: str = "possible underwater contact"
    status: str = "DETECTED"


@dataclass(frozen=True)
class SonarSweep:
    sensor_id: str
    mode: SonarMode
    timestamp_ns: int
    contacts: tuple[SonarContact, ...]
    targets_considered: int
    detections_missed: int


def simulate_sonar_sweep(
    sensor: SonarSensor,
    targets: Sequence[UnderwaterTarget],
    *,
    sensor_position_m: tuple[float, float],
    timestamp_ns: int,
    sea_state_noise: float = 0.0,
) -> SonarSweep:
    """Generate repeatable sonar observations from simulated underwater truth.

    Detection is a deliberately simple configurable game model, not a real-world
    sonar-performance prediction. A deterministic hash provides repeatable noise.
    """
    if len(sensor_position_m) != 2 or not all(isfinite(v) for v in sensor_position_m):
        raise ValueError("sensor_position_m must contain two finite coordinates")
    if isinstance(timestamp_ns, bool) or not isinstance(timestamp_ns, int) or timestamp_ns < 0:
        raise ValueError("timestamp_ns must be a non-negative integer")
    if not isfinite(sea_state_noise) or not 0 <= sea_state_noise <= 1:
        raise ValueError("sea_state_noise must be in [0, 1]")
    contacts: list[SonarContact] = []
    missed = 0
    sx, sy = sensor_position_m
    for target in targets:
        horizontal_range = hypot(target.x_m - sx, target.y_m - sy)
        slant_range = hypot(horizontal_range, target.depth_m)
        if slant_range > sensor.max_range_m:
            missed += 1
            continue
        noise = min(1.0, sensor.environmental_noise + sea_state_noise)
        mode_factor = 0.12 if sensor.mode is SonarMode.ACTIVE else (0.38 if target.moving else 0.12)
        signal = target.acoustic_signature * mode_factor
        threshold = max(0.0, noise + (1.0 - sensor.sensitivity) * 0.25)
        # Stable pseudo-noise ensures the same scenario replays identically.
        token = f"{sensor.sensor_id}|{target.target_id}|{timestamp_ns}|{sensor.mode.value}"
        sample = int.from_bytes(__import__("hashlib").sha256(token.encode()).digest()[:4], "big") / 0xFFFFFFFF
        if signal < threshold or sample < noise * 0.2:
            missed += 1
            continue
        confidence = max(0.05, min(0.99, signal / max(0.01, signal + noise)))
        range_error = (sample - 0.5) * 2 * sensor.range_uncertainty_fraction * slant_range
        estimated_range = max(0.0, slant_range + range_error)
        bearing = (degrees(atan2(target.y_m - sy, target.x_m - sx)) + 360.0) % 360.0
        contacts.append(SonarContact(
            contact_id=f"{sensor.sensor_id}-contact-{len(contacts) + 1}",
            sensor_id=sensor.sensor_id,
            mode=sensor.mode,
            timestamp_ns=timestamp_ns,
            estimated_range_m=estimated_range,
            estimated_bearing_deg=bearing,
            confidence=confidence,
            range_uncertainty_m=max(1.0, slant_range * sensor.range_uncertainty_fraction),
        ))
    return SonarSweep(sensor.sensor_id, sensor.mode, timestamp_ns, tuple(contacts), len(targets), missed)


def render_sonar_terminal(sweep: SonarSweep) -> str:
    """Render only sensor returns for the operator terminal; never render simulation truth."""
    lines = [
        f"SONAR {sweep.sensor_id} | {sweep.mode.value.upper()} | t={sweep.timestamp_ns}ns",
        f"CONTACTS: {len(sweep.contacts)} | MISSED/NOT DETECTED: {sweep.detections_missed}",
    ]
    if not sweep.contacts:
        lines.append("No sonar contacts reported.")
    for contact in sweep.contacts:
        age = "CURRENT" if contact.status == "DETECTED" else contact.status
        lines.append(
            f"{contact.contact_id}: {contact.classification}; "
            f"range~{contact.estimated_range_m:.0f}m +/-{contact.range_uncertainty_m:.0f}m; "
            f"bearing~{contact.estimated_bearing_deg:.0f}deg; "
            f"confidence={contact.confidence:.2f}; {age}"
        )
    return "\n".join(lines)

def append_sonar_sweep_to_ledger(sweep, ledger) -> int:
    """Bridge simulated sonar returns into VIGIL's normalized sensor-event ledger.

    Only estimated contact measurements and aggregate sweep status cross this
    boundary; simulation target IDs and coordinates are never serialized.
    """
    from .sensor_event import SensorEventRecord, SensorEventStatus, SensorEventLedger

    if not isinstance(sweep, SonarSweep):
        raise TypeError("sweep must be a SonarSweep")
    if not isinstance(ledger, SensorEventLedger):
        raise TypeError("ledger must be a SensorEventLedger")
    count = 0
    for contact in sweep.contacts:
        event = SensorEventRecord(
            event_id=f"sonar:{contact.sensor_id}:{contact.timestamp_ns}:{contact.contact_id}",
            sensor_id=contact.sensor_id,
            timestamp_ns=contact.timestamp_ns,
            modality="acoustic_sonar",
            event_kind="sonar_contact",
            status=SensorEventStatus.ACCEPTED,
            reason="Simulated sonar return; estimated range and bearing only, not target identity or ground truth.",
            confidence=contact.confidence,
            evidence_score=contact.confidence,
            uncertainty_m=contact.range_uncertainty_m,
            calibration_status="simulation_only",
            model_id="vigil-underwater-simulation",
            model_revision="1",
        )
        ledger.append(event)
        count += 1
    # Keep a sweep-level status even when no contact was detected.
    if not sweep.contacts:
        ledger.append(SensorEventRecord(
            event_id=f"sonar:{sweep.sensor_id}:{sweep.timestamp_ns}:empty-sweep",
            sensor_id=sweep.sensor_id,
            timestamp_ns=sweep.timestamp_ns,
            modality="acoustic_sonar",
            event_kind="sonar_sweep_no_contact",
            status=SensorEventStatus.CONTEXT,
            reason=f"No contact reported; {sweep.detections_missed} target(s) missed or outside range.",
            confidence=0.0,
            evidence_score=0.0,
            calibration_status="simulation_only",
            model_id="vigil-underwater-simulation",
            model_revision="1",
        ))
        count += 1
    return count
