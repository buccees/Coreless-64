"""Explicit sensor-local to model-frame rigid transforms.

Transforms are calibration records, not guesses: callers must deliberately opt into
this API for observations known to be expressed in the named sensor-local frame.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable


@dataclass(frozen=True)
class SensorMountTransform:
    mount_id: str
    sensor_id: str
    model_id: str
    model_revision: str
    frame_id: str
    source_frame_id: str
    translation_m: tuple[float, float, float]
    rotation_matrix: tuple[float, float, float, float, float, float, float, float, float]
    verified: bool = False

    def __post_init__(self) -> None:
        if not all(isinstance(value, str) and value.strip() for value in (
            self.mount_id, self.sensor_id, self.model_id, self.model_revision,
            self.frame_id, self.source_frame_id,
        )):
            raise ValueError("mount, sensor, model, revision, and frame IDs are required")
        if self.source_frame_id == self.frame_id:
            raise ValueError("sensor-local source frame must differ from model frame")
        if len(self.translation_m) != 3 or not all(isfinite(v) for v in self.translation_m):
            raise ValueError("translation_m must contain three finite values")
        if len(self.rotation_matrix) != 9 or not all(isfinite(v) for v in self.rotation_matrix):
            raise ValueError("rotation_matrix must contain nine finite values")
        if not isinstance(self.verified, bool):
            raise ValueError("verified must be a boolean")
        rows = (self.rotation_matrix[0:3], self.rotation_matrix[3:6], self.rotation_matrix[6:9])
        tolerance = 1e-5
        for i, row in enumerate(rows):
            for j, other in enumerate(rows):
                dot = sum(a * b for a, b in zip(row, other))
                expected = 1.0 if i == j else 0.0
                if abs(dot - expected) > tolerance:
                    raise ValueError("rotation_matrix must be orthonormal")
        a, b, c, d, e, f, g, h, i = self.rotation_matrix
        determinant = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
        if abs(determinant - 1.0) > tolerance:
            raise ValueError("rotation_matrix must have determinant +1")

    def transform_position(self, position_m: Iterable[float]) -> tuple[float, float, float]:
        values = tuple(position_m)
        if len(values) != 3 or not all(isfinite(v) for v in values):
            raise ValueError("position_m must contain three finite values")
        x, y, z = values
        r = self.rotation_matrix
        tx, ty, tz = self.translation_m
        return (
            r[0] * x + r[1] * y + r[2] * z + tx,
            r[3] * x + r[4] * y + r[5] * z + ty,
            r[6] * x + r[7] * y + r[8] * z + tz,
        )
