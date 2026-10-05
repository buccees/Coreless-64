"""Hardware-independent VIGIL simulation/replay foundation."""
from __future__ import annotations
from dataclasses import dataclass
from .model import Observation


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
