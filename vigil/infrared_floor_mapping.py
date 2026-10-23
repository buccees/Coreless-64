"""Calibrated infrared/thermal samples projected onto a registered floor plan.

This is a geometry adapter, not a camera driver or thermal-image decoder. An
upstream IR sensor adapter supplies pixel samples and optional temperature
values; a surveyed raster calibration maps them into the model frame.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, hypot, sqrt
from typing import Sequence

from .raster_calibration import RasterBlueprintCalibration


@dataclass(frozen=True)
class InfraredPixelSample:
    pixel_x: float
    pixel_y: float
    intensity: float
    temperature_c: float | None = None
    pixel_uncertainty: float = 1.0
    label: str = ""
    association_id: str | None = None

    def __post_init__(self) -> None:
        if not all(isfinite(v) for v in (self.pixel_x, self.pixel_y, self.intensity,
                                         self.pixel_uncertainty)):
            raise ValueError("infrared sample values must be finite")
        if not 0.0 <= self.intensity <= 1.0:
            raise ValueError("intensity must be normalized to [0, 1]")
        if self.temperature_c is not None and not isfinite(self.temperature_c):
            raise ValueError("temperature_c must be finite when supplied")
        if self.pixel_uncertainty < 0:
            raise ValueError("pixel_uncertainty cannot be negative")
        if self.association_id is not None and not self.association_id.strip():
            raise ValueError("association_id must be non-empty when provided")


@dataclass(frozen=True)
class MappedInfraredSample:
    sensor_id: str
    model_id: str
    model_revision: str
    frame_id: str
    level_id: str
    timestamp_ns: int
    position_m: tuple[float, float, float]
    intensity: float
    temperature_c: float | None
    uncertainty_m: float
    label: str
    association_id: str | None = None


@dataclass(frozen=True)
class InfraredFloorMap:
    sensor_id: str
    model_id: str
    model_revision: str
    frame_id: str
    level_id: str
    timestamp_ns: int
    image_width: int
    image_height: int
    calibration_rms_m: float
    samples: tuple[MappedInfraredSample, ...]
    calibration_id: str | None = None
    sensor_mount_id: str | None = None


class InfraredFloorMapper:
    """Project calibrated IR pixel samples into a floor-plan coordinate frame.

    The calibration must refer to the intended model revision, frame, and floor.
    Input intensity is a unitless normalized value; temperature is only carried
    through when the upstream sensor provides a calibrated temperature.
    """

    def __init__(
        self,
        calibration: RasterBlueprintCalibration,
        *,
        sensor_id: str,
        image_width: int,
        image_height: int,
        calibration_id: str | None = None,
        sensor_mount_id: str | None = None,
    ) -> None:
        if not sensor_id.strip():
            raise ValueError("sensor_id is required")
        if isinstance(image_width, bool) or not isinstance(image_width, int) or image_width <= 0:
            raise ValueError("image_width must be a positive integer")
        if isinstance(image_height, bool) or not isinstance(image_height, int) or image_height <= 0:
            raise ValueError("image_height must be a positive integer")
        if calibration_id is not None and not calibration_id.strip():
            raise ValueError("calibration_id must be non-empty when provided")
        if sensor_mount_id is not None and not sensor_mount_id.strip():
            raise ValueError("sensor_mount_id must be non-empty when provided")
        self.calibration = calibration
        self.sensor_id = sensor_id
        self.image_width = image_width
        self.image_height = image_height
        self.calibration_id = calibration_id
        self.sensor_mount_id = sensor_mount_id

    def map_frame(
        self,
        samples: Sequence[InfraredPixelSample],
        *,
        timestamp_ns: int,
    ) -> InfraredFloorMap:
        if isinstance(timestamp_ns, bool) or not isinstance(timestamp_ns, int) or timestamp_ns < 0:
            raise ValueError("timestamp_ns must be a non-negative integer")
        mapped = []
        a, b, _ = self.calibration.x_coefficients
        d, e, _ = self.calibration.y_coefficients
        # Conservative worst-axis metric scale, combined with fit residual.
        metres_per_pixel = max(hypot(a, d), hypot(b, e))
        for sample in samples:
            if not isinstance(sample, InfraredPixelSample):
                raise TypeError("samples must contain InfraredPixelSample values")
            if not (0 <= sample.pixel_x < self.image_width and
                    0 <= sample.pixel_y < self.image_height):
                raise ValueError("infrared sample lies outside the calibrated image")
            mapped.append(MappedInfraredSample(
                sensor_id=self.sensor_id,
                model_id=self.calibration.model_id,
                model_revision=self.calibration.model_revision,
                frame_id=self.calibration.frame_id,
                level_id=self.calibration.level_id,
                timestamp_ns=timestamp_ns,
                position_m=self.calibration.pixel_to_model(sample.pixel_x, sample.pixel_y),
                intensity=sample.intensity,
                temperature_c=sample.temperature_c,
                uncertainty_m=sqrt(
                    self.calibration.rms_residual_m ** 2
                    + (sample.pixel_uncertainty * metres_per_pixel) ** 2
                ),
                label=sample.label,
                association_id=sample.association_id,
            ))
        return InfraredFloorMap(
            sensor_id=self.sensor_id,
            model_id=self.calibration.model_id,
            model_revision=self.calibration.model_revision,
            frame_id=self.calibration.frame_id,
            level_id=self.calibration.level_id,
            timestamp_ns=timestamp_ns,
            image_width=self.image_width,
            image_height=self.image_height,
            calibration_rms_m=self.calibration.rms_residual_m,
            samples=tuple(mapped),
            calibration_id=self.calibration_id,
            sensor_mount_id=self.sensor_mount_id,
        )
