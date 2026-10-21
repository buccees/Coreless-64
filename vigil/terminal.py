"""Green-phosphor terminal view for VIGIL spatial-awareness state.

This is a renderer, not a hardware driver or a live sensor loop. Call render()
with the current registered blueprint, pose estimate, observations, and monotonic
timestamp supplied by Coreless-owned adapters.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Sequence

from .blueprint import BlueprintModel, PoseEstimate, PoseState, nearest_feature
from .positioning import SpatialObservation


_GREEN = "\\033[92m"
_DIM = "\\033[32m"
_RESET = "\\033[0m"


@dataclass(frozen=True)
class SensorLine:
    source_id: str
    state: str
    age_ms: int | None
    uncertainty_m: float | None


class VigilTerminal:
    """Render a compact, dependency-free green terminal status panel."""

    def __init__(self, *, color: bool = True, max_sensor_age_ns: int = 2_000_000_000) -> None:
        if max_sensor_age_ns < 0:
            raise ValueError("max_sensor_age_ns must be non-negative")
        self.color = color
        self.max_sensor_age_ns = max_sensor_age_ns

    def sensor_lines(
        self, observations: Sequence[SpatialObservation], *, now_ns: int
    ) -> tuple[SensorLine, ...]:
        if now_ns < 0:
            raise ValueError("now_ns must be non-negative")
        latest: dict[str, SpatialObservation] = {}
        for item in observations:
            if item.timestamp_ns > now_ns:
                continue
            previous = latest.get(item.source_id)
            if previous is None or item.timestamp_ns > previous.timestamp_ns:
                latest[item.source_id] = item
        lines = []
        for source_id in sorted(latest):
            item = latest[source_id]
            age_ns = now_ns - item.timestamp_ns
            fresh = age_ns <= self.max_sensor_age_ns
            lines.append(SensorLine(
                source_id=source_id,
                state="ONLINE" if fresh else "STALE",
                age_ms=age_ns // 1_000_000,
                uncertainty_m=item.uncertainty_m,
            ))
        return tuple(lines)

    def render(
        self,
        model: BlueprintModel | None,
        pose: PoseEstimate | None,
        observations: Sequence[SpatialObservation] = (),
        *,
        now_ns: int,
        selected_level: str | None = None,
    ) -> str:
        """Return terminal text; missing/stale data is shown explicitly as unknown."""
        if now_ns < 0:
            raise ValueError("now_ns must be non-negative")
        lines = [
            "╔══════════════════════════════════════════════════════════════╗",
            "║  V I G I L   //   SPATIAL AWARENESS TERMINAL                ║",
            "╠══════════════════════════════════════════════════════════════╣",
        ]
        if model is None:
            lines.append("║ BLUEPRINT : NO MODEL REGISTERED                              ║")
        else:
            lines.append(f"║ BLUEPRINT : {self._fit(model.model_id + ' / ' + model.revision, 44)}║")
            lines.append(f"║ FRAME     : {self._fit(model.frame_id, 44)}║")
        lines.append(f"║ ACTIVE LEVEL: {self._fit(selected_level or 'AUTO / UNKNOWN', 44)}║")

        if pose is None:
            lines.extend([
                "║ TRACKING  : UNINITIALIZED                                   ║",
                "║ POSITION  : X ---.---  Y ---.---  Z ---.--- m               ║",
                "║ FLOOR/ZONE: UNKNOWN                                          ║",
                "║ UNCERTAINTY: UNKNOWN                                         ║",
            ])
        else:
            lines.append(f"║ TRACKING  : {self._fit(pose.state.value, 44)}║")
            if pose.position_m is None:
                position_text = "X UNKNOWN  Y UNKNOWN  Z UNKNOWN"
            else:
                x, y, z = pose.position_m
                position_text = f"X {x:8.3f}  Y {y:8.3f}  Z {z:8.3f} m"
            lines.append(f"║ POSITION  : {self._fit(position_text, 44)}║")
            if model is not None and pose.position_m is not None and (
                pose.model_id == model.model_id
                and pose.model_revision == model.revision
                and pose.frame_id == model.frame_id
            ):
                match = nearest_feature(model, pose.position_m)
            else:
                match = None
            if match is None:
                location = "UNKNOWN"
            else:
                feature, distance = match
                floor = feature.level or "?"
                zone = feature.zone or feature.label
                location = f"{floor} / {zone} ({distance:.1f}m to anchor)"
            lines.append(f"║ FLOOR/ZONE: {self._fit(location, 44)}║")
            uncertainty = (
                "UNKNOWN" if pose.uncertainty_m is None
                else f"±{pose.uncertainty_m:.2f} m"
            )
            lines.append(f"║ UNCERTAINTY: {self._fit(uncertainty, 43)} ║")

        lines.append("╟──────────────────── SENSOR TELEMETRY ────────────────────────╢")
        sensor_lines = self.sensor_lines(observations, now_ns=now_ns)
        if not sensor_lines:
            lines.append("║ No sensor observations received                               ║")
        else:
            for sensor in sensor_lines[:4]:
                age = "unknown" if sensor.age_ms is None else f"{sensor.age_ms}ms"
                uncertainty = (
                    "?" if sensor.uncertainty_m is None
                    else f"±{sensor.uncertainty_m:.2f}m"
                )
                detail = f"{sensor.source_id}: {sensor.state} age={age} σ={uncertainty}"
                lines.append(f"║ {self._fit(detail, 60)}║")
            if len(sensor_lines) > 4:
                lines.append(f"║ + {len(sensor_lines) - 4} additional sensor sources                                  ║")
        lines.extend([
            "╟──────────────────────────────────────────────────────────────╢",
            "║ CORELESS OWNS INPUT  |  VIGIL IS OPTIONAL  |  FAIL-OPEN       ║",
            "╚══════════════════════════════════════════════════════════════╝",
        ])
        rendered = "\n".join(lines)
        if not self.color:
            return rendered
        # Color only the rendered text; no terminal control input is interpreted.
        return _GREEN + rendered.replace("SENSOR TELEMETRY", _DIM + "SENSOR TELEMETRY" + _GREEN) + _RESET

    @staticmethod
    def _fit(value: str, width: int) -> str:
        # Keep terminal fields stable even if blueprint metadata is untrusted/long.
        safe = "".join(ch if ch.isprintable() and ch != "\\x1b" else "?" for ch in value)
        if len(safe) > width:
            safe = safe[: max(0, width - 3)] + "..."
        return safe.ljust(width)
