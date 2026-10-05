"""Hardware-independent VIGIL simulation/replay foundation."""
from __future__ import annotations
from dataclasses import dataclass
from .model import Observation
from .provenance import EventProvenance


@dataclass(frozen=True)
class SimulationFrame:
    timestamp_ns: int
    observations: tuple[Observation, ...]


class ReplaySource:
    def __init__(self, frames: tuple[SimulationFrame, ...] = ()) -> None:
        self._frames = tuple(sorted(frames, key=lambda frame: frame.timestamp_ns))
        self._index = 0

    def reset(self) -> None:
        self._index = 0

    def next(self) -> SimulationFrame | None:
        if self._index >= len(self._frames):
            return None
        frame = self._frames[self._index]
        self._index += 1
        return frame


@dataclass(frozen=True)
class ReplayEvent:
    event_id: str
    timestamp_ns: int
    kind: str
    payload: object
    provenance: EventProvenance | None = None


@dataclass(frozen=True)
class ReplayValidation:
    valid: bool
    event_count: int
    mismatches: tuple[str, ...] = ()


class ReplayLog:
    """Deterministic append-only VIGIL event log for audit and replay."""
    def __init__(self, events: tuple[ReplayEvent, ...] = ()) -> None:
        self._events = tuple(events)
        self._last_timestamp = self._events[-1].timestamp_ns if self._events else -1

    @property
    def events(self) -> tuple[ReplayEvent, ...]:
        return self._events

    def append(self, event: ReplayEvent) -> None:
        if event.timestamp_ns < self._last_timestamp:
            raise ValueError("replay events must be monotonic by timestamp")
        if any(existing.event_id == event.event_id for existing in self._events):
            raise ValueError("replay event_id must be unique")
        self._events = self._events + (event,)
        self._last_timestamp = event.timestamp_ns

    def reset(self) -> None:
        self._last_timestamp = self._events[-1].timestamp_ns if self._events else -1

    def replay(self) -> tuple[ReplayEvent, ...]:
        return self._events
