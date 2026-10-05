"""Coordinate mapping for camera-derived Coreless touch input."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CameraDisplayMapper:
    """Map camera pixel coordinates into display coordinates deterministically."""

    camera_width: int
    camera_height: int
    display_width: int
    display_height: int
    clamp: bool = True

    def __post_init__(self) -> None:
        if min(self.camera_width, self.camera_height, self.display_width, self.display_height) <= 0:
            raise ValueError("camera and display dimensions must be positive")

    def map(self, x: float, y: float) -> tuple[float, float]:
        if self.clamp:
            x = min(max(x, 0.0), float(self.camera_width))
            y = min(max(y, 0.0), float(self.camera_height))
        elif not 0.0 <= x <= self.camera_width or not 0.0 <= y <= self.camera_height:
            raise ValueError("camera coordinates are outside the source frame")
        return (
            x * self.display_width / self.camera_width,
            y * self.display_height / self.camera_height,
        )
