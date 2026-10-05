"""Shared single-reader camera source for Coreless-native VIGIL."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol

from .spatial import CameraFrame


class CameraReader(Protocol):
    def available(self) -> bool:
        ...

    def read(self) -> CameraFrame | None:
        ...


@dataclass
class SharedCameraSource:
    """Own one physical camera reader and expose its newest frame to consumers.

    Only this object reads the underlying camera. VIGIL perception, fast touch,
    and other consumers receive the same captured frame instead of competing
    for separate camera sessions.
    """

    source: CameraReader
    _latest: CameraFrame | None = None
    _last_sequence: int | None = None

    def available(self) -> bool:
        return self.source.available()

    def capture(self) -> CameraFrame | None:
        if not self.source.available():
            return None
        frame = self.source.read()
        if frame is not None:
            if self._last_sequence is not None and frame.sequence <= self._last_sequence:
                raise ValueError("shared camera frame sequence must increase monotonically")
            self._latest = frame
            self._last_sequence = frame.sequence
        return frame

    def latest(self) -> CameraFrame | None:
        return self._latest

    def poll(self) -> CameraFrame | None:
        return self.capture()

    def persistent_state(self) -> Mapping[str, object]:
        return {
            "version": 1,
            "source_id": self._latest.source_id if self._latest else None,
            "last_sequence": self._last_sequence,
        }

    def restore_state(self, state: Mapping[str, object]) -> None:
        if not isinstance(state, Mapping) or int(state.get("version", 1)) != 1:
            raise ValueError("unsupported shared camera state version")
        sequence = state.get("last_sequence")
        if sequence is not None:
            sequence = int(sequence)
            if sequence < 0:
                raise ValueError("camera last_sequence must be non-negative")
        self._latest = None
        self._last_sequence = sequence
