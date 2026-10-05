"""Coreless-native VIGIL touch and gesture interpretation."""
from __future__ import annotations

from dataclasses import dataclass
from math import atan2, degrees, hypot
from typing import Mapping

from reference.input import InputEvent, InputEventType


@dataclass(frozen=True)
class TouchPoint:
    contact_id: int
    x: float
    y: float
    timestamp_ns: int


@dataclass(frozen=True)
class GestureResult:
    gesture: str
    contacts: tuple[int, ...]
    source_sequence: tuple[int, ...]
    confidence: float = 1.0
    metadata: Mapping[str, object] | None = None

    def __post_init__(self) -> None:
        if not self.contacts or not self.source_sequence:
            raise ValueError("gesture requires contacts and source sequence")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


class GestureInterpreter:
    """Deterministic tap, swipe, hold, and two-contact gesture state machine."""

    def __init__(
        self,
        movement_threshold: float = 20.0,
        tap_window_ns: int = 350_000_000,
        long_press_ns: int = 600_000_000,
    ) -> None:
        if movement_threshold < 0 or tap_window_ns <= 0 or long_press_ns <= 0:
            raise ValueError("gesture thresholds must be positive")
        self.movement_threshold = movement_threshold
        self.tap_window_ns = tap_window_ns
        self.long_press_ns = long_press_ns
        self._contacts: dict[int, TouchPoint] = {}
        self._starts: dict[int, TouchPoint] = {}
        self._last_tap: tuple[int, int, int, float, float] | None = None
        self._pair_start_distance: float | None = None
        self._pair_start_angle: float | None = None
        self._pair_contacts: tuple[int, int] | None = None

    @property
    def active_contacts(self) -> tuple[int, ...]:
        return tuple(sorted(self._contacts))

    def process(self, event: InputEvent) -> tuple[GestureResult, ...]:
        if event.event_type not in {InputEventType.TOUCH_BEGIN, InputEventType.TOUCH_UPDATE, InputEventType.TOUCH_END}:
            return ()
        if event.contact_id is None or event.x is None or event.y is None:
            raise ValueError("touch events require contact_id and coordinates")
        point = TouchPoint(event.contact_id, event.x, event.y, event.timestamp_ns)

        if event.event_type is InputEventType.TOUCH_BEGIN:
            if event.contact_id in self._contacts:
                raise ValueError("touch contact is already active")
            self._contacts[event.contact_id] = point
            self._starts[event.contact_id] = point
            if len(self._contacts) == 2:
                ids = tuple(sorted(self._contacts))
                a, b = (self._contacts[ids[0]], self._contacts[ids[1]])
                self._pair_contacts = ids
                self._pair_start_distance = hypot(b.x - a.x, b.y - a.y)
                self._pair_start_angle = degrees(atan2(b.y - a.y, b.x - a.x))
            return ()

        if event.contact_id not in self._contacts:
            raise ValueError("touch update/end without active contact")
        self._contacts[event.contact_id] = point

        if event.event_type is InputEventType.TOUCH_UPDATE:
            return self._update(event.sequence)

        result = self._end(event.sequence, event.contact_id, point)
        self._contacts.pop(event.contact_id)
        self._starts.pop(event.contact_id)
        if len(self._contacts) < 2:
            self._pair_contacts = None
            self._pair_start_distance = None
            self._pair_start_angle = None
        return result

    def _update(self, sequence: int) -> tuple[GestureResult, ...]:
        if len(self._contacts) != 2 or self._pair_contacts is None:
            return ()
        ids = self._pair_contacts
        a, b = (self._contacts[ids[0]], self._contacts[ids[1]])
        distance = hypot(b.x - a.x, b.y - a.y)
        angle = degrees(atan2(b.y - a.y, b.x - a.x))
        results: list[GestureResult] = []
        if self._pair_start_distance is not None and abs(distance - self._pair_start_distance) >= self.movement_threshold:
            kind = "pinch_out" if distance > self._pair_start_distance else "pinch_in"
            results.append(GestureResult(
                kind, ids, (sequence,),
                metadata={"scale": distance / self._pair_start_distance, "distance": distance},
            ))
        if self._pair_start_angle is not None:
            delta = (angle - self._pair_start_angle + 180.0) % 360.0 - 180.0
            if abs(delta) >= 10.0:
                results.append(GestureResult("rotate", ids, (sequence,), metadata={"angle_degrees": delta}))
        return tuple(results)

    def _end(self, sequence: int, contact_id: int, point: TouchPoint) -> tuple[GestureResult, ...]:
        start = self._starts[contact_id]
        duration = point.timestamp_ns - start.timestamp_ns
        distance = hypot(point.x - start.x, point.y - start.y)
        if distance < self.movement_threshold:
            if duration >= self.long_press_ns:
                return (GestureResult("long_press", (contact_id,), (sequence,), metadata={"duration_ns": duration}),)
            if self._last_tap is not None:
                last_time, last_contact, last_sequence, last_x, last_y = self._last_tap
                if (
                    contact_id == last_contact
                    and point.timestamp_ns - last_time <= self.tap_window_ns
                    and hypot(point.x - last_x, point.y - last_y) < self.movement_threshold
                ):
                    self._last_tap = None
                    return (GestureResult("double_tap", (contact_id,), (last_sequence, sequence)),)
            self._last_tap = (point.timestamp_ns, contact_id, sequence, point.x, point.y)
            return (GestureResult("tap", (contact_id,), (sequence,)))
        angle = degrees(atan2(point.y - start.y, point.x - start.x))
        direction = "right" if -45 <= angle < 45 else "up" if 45 <= angle < 135 else "left" if angle >= 135 or angle < -135 else "down"
        return (GestureResult("swipe", (contact_id,), (sequence,), metadata={"direction": direction, "distance": distance, "duration_ns": duration}),)
