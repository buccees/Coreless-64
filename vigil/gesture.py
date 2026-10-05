"""Coreless-native VIGIL touch and gesture interpretation."""
from __future__ import annotations

from dataclasses import dataclass
from math import atan2, degrees, hypot
from typing import Mapping

from reference.input import InputEvent, InputEventType, InterpretedInputEvent


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
    metadata: Mapping[str, object] = None

    def __post_init__(self) -> None:
        if not self.contacts or not self.source_sequence:
            raise ValueError("gesture requires contacts and source sequence")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


class GestureInterpreter:
    """Deterministic gesture state machine over authoritative Coreless events."""

    def __init__(self, movement_threshold: float = 20.0) -> None:
        if movement_threshold < 0:
            raise ValueError("movement_threshold must be non-negative")
        self.movement_threshold = movement_threshold
        self._contacts: dict[int, TouchPoint] = {}
        self._starts: dict[int, TouchPoint] = {}
        self._sequences: list[int] = []

    @property
    def active_contacts(self) -> tuple[int, ...]:
        return tuple(sorted(self._contacts))

    def process(self, event: InputEvent) -> tuple[GestureResult, ...]:
        if event.event_type not in {
            InputEventType.TOUCH_BEGIN,
            InputEventType.TOUCH_UPDATE,
            InputEventType.TOUCH_END,
        }:
            return ()
        if event.contact_id is None or event.x is None or event.y is None:
            raise ValueError("touch events require contact_id and coordinates")
        point = TouchPoint(event.contact_id, event.x, event.y, event.timestamp_ns)
        self._sequences.append(event.sequence)
        if event.event_type is InputEventType.TOUCH_BEGIN:
            self._contacts[event.contact_id] = point
            self._starts[event.contact_id] = point
            return ()
        if event.contact_id not in self._contacts:
            raise ValueError("touch update/end without active contact")
        previous = self._contacts[event.contact_id]
        self._contacts[event.contact_id] = point
        if event.event_type is InputEventType.TOUCH_UPDATE:
            return self._update_gesture(previous, point)
        result = self._end_gesture(event.contact_id, point)
        self._contacts.pop(event.contact_id, None)
        self._starts.pop(event.contact_id, None)
        return result

    def _update_gesture(self, previous: TouchPoint, current: TouchPoint) -> tuple[GestureResult, ...]:
        contacts = tuple(sorted(self._contacts))
        if len(contacts) >= 2:
            points = tuple(self._contacts[key] for key in contacts)
            span = hypot(points[1].x - points[0].x, points[1].y - points[0].y)
            return (GestureResult("multitouch_update", contacts, tuple(self._sequences[-len(contacts):]), metadata={"span": span}),)
        return ()

    def _end_gesture(self, contact_id: int, point: TouchPoint) -> tuple[GestureResult, ...]:
        start = self._starts[contact_id]
        dx = point.x - start.x
        dy = point.y - start.y
        distance = hypot(dx, dy)
        if distance < self.movement_threshold:
            return (GestureResult("tap", (contact_id,), tuple(self._sequences[-1:])),)
        angle = degrees(atan2(dy, dx))
        direction = "right" if -45 <= angle < 45 else "up" if 45 <= angle < 135 else "left" if angle >= 135 or angle < -135 else "down"
        return (GestureResult("swipe", (contact_id,), tuple(self._sequences[-1:]), metadata={"direction": direction, "distance": distance}),)
