"""Calibrated raster-blueprint to model-frame coordinate mapping.

This module aligns a scanned floor-plan image using surveyed/manual control
points. It does not perform OCR, line detection, CAD extraction, or image loading.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, sqrt
from typing import Sequence


@dataclass(frozen=True)
class RasterControlPoint:
    pixel_x: float
    pixel_y: float
    model_x_m: float
    model_y_m: float
    label: str = ""

    def __post_init__(self) -> None:
        if not all(isfinite(v) for v in (
            self.pixel_x, self.pixel_y, self.model_x_m, self.model_y_m
        )):
            raise ValueError("control point coordinates must be finite")


def _solve_3x3(matrix: list[list[float]], rhs: list[float]) -> tuple[float, float, float]:
    augmented = [row[:] + [value] for row, value in zip(matrix, rhs)]
    for col in range(3):
        pivot = max(range(col, 3), key=lambda row: abs(augmented[row][col]))
        if abs(augmented[pivot][col]) < 1e-12:
            raise ValueError("control points are collinear or geometrically degenerate")
        augmented[col], augmented[pivot] = augmented[pivot], augmented[col]
        divisor = augmented[col][col]
        augmented[col] = [value / divisor for value in augmented[col]]
        for row in range(3):
            if row == col:
                continue
            factor = augmented[row][col]
            augmented[row] = [
                a - factor * b for a, b in zip(augmented[row], augmented[col])
            ]
    return augmented[0][3], augmented[1][3], augmented[2][3]


def _fit_axis(points: Sequence[RasterControlPoint], target: str) -> tuple[float, float, float]:
    # Fit target = a * pixel_x + b * pixel_y + c using least squares.
    rows = [(point.pixel_x, point.pixel_y, 1.0) for point in points]
    values = [getattr(point, target) for point in points]
    normal = [
        [sum(row[i] * row[j] for row in rows) for j in range(3)]
        for i in range(3)
    ]
    rhs = [sum(row[i] * value for row, value in zip(rows, values)) for i in range(3)]
    return _solve_3x3(normal, rhs)


@dataclass(frozen=True)
class RasterBlueprintCalibration:
    model_id: str
    model_revision: str
    frame_id: str
    level_id: str
    elevation_m: float
    x_coefficients: tuple[float, float, float]
    y_coefficients: tuple[float, float, float]
    control_point_count: int
    rms_residual_m: float
    control_labels: tuple[str, ...]

    @classmethod
    def fit(
        cls,
        *,
        model_id: str,
        model_revision: str,
        frame_id: str,
        level_id: str,
        elevation_m: float,
        control_points: Sequence[RasterControlPoint],
    ) -> "RasterBlueprintCalibration":
        if not all(isinstance(v, str) and v.strip() for v in (
            model_id, model_revision, frame_id, level_id
        )):
            raise ValueError("model, revision, frame, and level IDs are required")
        if not isfinite(elevation_m):
            raise ValueError("elevation_m must be finite")
        if len(control_points) < 3:
            raise ValueError("at least three control points are required for affine calibration")
        x_coefficients = _fit_axis(control_points, "model_x_m")
        y_coefficients = _fit_axis(control_points, "model_y_m")
        residuals = []
        for point in control_points:
            predicted_x = sum(a * b for a, b in zip(
                x_coefficients, (point.pixel_x, point.pixel_y, 1.0)
            ))
            predicted_y = sum(a * b for a, b in zip(
                y_coefficients, (point.pixel_x, point.pixel_y, 1.0)
            ))
            residuals.append(sqrt(
                (predicted_x - point.model_x_m) ** 2
                + (predicted_y - point.model_y_m) ** 2
            ))
        rms = sqrt(sum(residual * residual for residual in residuals) / len(residuals))
        return cls(
            model_id, model_revision, frame_id, level_id, elevation_m,
            x_coefficients, y_coefficients, len(control_points), rms,
            tuple(point.label for point in control_points if point.label),
        )

    def pixel_to_model(self, pixel_x: float, pixel_y: float) -> tuple[float, float, float]:
        if not isfinite(pixel_x) or not isfinite(pixel_y):
            raise ValueError("pixel coordinates must be finite")
        x = sum(a * b for a, b in zip(
            self.x_coefficients, (pixel_x, pixel_y, 1.0)
        ))
        y = sum(a * b for a, b in zip(
            self.y_coefficients, (pixel_x, pixel_y, 1.0)
        ))
        return x, y, self.elevation_m

    def model_to_pixel(self, model_x_m: float, model_y_m: float) -> tuple[float, float]:
        if not isfinite(model_x_m) or not isfinite(model_y_m):
            raise ValueError("model coordinates must be finite")
        a, b, c = self.x_coefficients
        d, e, f = self.y_coefficients
        determinant = a * e - b * d
        if abs(determinant) < 1e-12:
            raise ValueError("calibration transform is not invertible")
        x = model_x_m - c
        y = model_y_m - f
        pixel_x = (x * e - b * y) / determinant
        pixel_y = (a * y - x * d) / determinant
        return pixel_x, pixel_y
