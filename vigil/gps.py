"""GPS-to-blueprint observation adapter.

GPS fixes are converted from WGS-84 geodetic coordinates into a local ENU
(East, North, Up) frame, then through an explicit registered transform into
the blueprint frame. This is not an indoor-positioning guarantee; GPS accuracy
is carried into the resulting observation and weak fixes remain uncertain.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import cos, isfinite, radians, sin, sqrt
from uuid import uuid4

from .blueprint import BlueprintModel, CoordinateTransform
from .positioning import SpatialObservation


_WGS84_A = 6378137.0
_WGS84_E2 = 6.69437999014e-3


@dataclass(frozen=True)
class GPSFix:
    latitude_deg: float
    longitude_deg: float
    altitude_m: float
    timestamp_ns: int
    horizontal_accuracy_m: float
    vertical_accuracy_m: float | None = None
    fix_id: str | None = None

    def __post_init__(self) -> None:
        values = (self.latitude_deg, self.longitude_deg, self.altitude_m,
                  self.horizontal_accuracy_m)
        if not all(isfinite(v) for v in values):
            raise ValueError("GPS fix values must be finite")
        if not -90 <= self.latitude_deg <= 90:
            raise ValueError("latitude must be between -90 and 90 degrees")
        if not -180 <= self.longitude_deg <= 180:
            raise ValueError("longitude must be between -180 and 180 degrees")
        if self.timestamp_ns < 0:
            raise ValueError("GPS timestamp must be non-negative")
        if self.horizontal_accuracy_m <= 0:
            raise ValueError("horizontal accuracy must be positive")
        if self.vertical_accuracy_m is not None and (
            not isfinite(self.vertical_accuracy_m) or self.vertical_accuracy_m <= 0
        ):
            raise ValueError("vertical accuracy must be finite and positive when supplied")


@dataclass(frozen=True)
class GeodeticAnchor:
    latitude_deg: float
    longitude_deg: float
    altitude_m: float
    frame_id: str = "gps-enu"

    def __post_init__(self) -> None:
        if not all(isfinite(v) for v in (
            self.latitude_deg, self.longitude_deg, self.altitude_m
        )):
            raise ValueError("GPS anchor values must be finite")
        if not -90 <= self.latitude_deg <= 90 or not -180 <= self.longitude_deg <= 180:
            raise ValueError("GPS anchor latitude or longitude is out of range")
        if not self.frame_id.strip():
            raise ValueError("GPS anchor frame_id must not be empty")


def _ecef(lat_deg: float, lon_deg: float, altitude_m: float) -> tuple[float, float, float]:
    lat, lon = radians(lat_deg), radians(lon_deg)
    sin_lat, cos_lat = sin(lat), cos(lat)
    radius = _WGS84_A / sqrt(1.0 - _WGS84_E2 * sin_lat * sin_lat)
    return (
        (radius + altitude_m) * cos_lat * cos(lon),
        (radius + altitude_m) * cos_lat * sin(lon),
        (radius * (1.0 - _WGS84_E2) + altitude_m) * sin_lat,
    )


def _to_enu(
    fix: GPSFix, anchor: GeodeticAnchor
) -> tuple[float, float, float]:
    x, y, z = _ecef(fix.latitude_deg, fix.longitude_deg, fix.altitude_m)
    x0, y0, z0 = _ecef(anchor.latitude_deg, anchor.longitude_deg, anchor.altitude_m)
    dx, dy, dz = x - x0, y - y0, z - z0
    lat0, lon0 = radians(anchor.latitude_deg), radians(anchor.longitude_deg)
    east = -sin(lon0) * dx + cos(lon0) * dy
    north = (
        -sin(lat0) * cos(lon0) * dx
        - sin(lat0) * sin(lon0) * dy
        + cos(lat0) * dz
    )
    up = (
        cos(lat0) * cos(lon0) * dx
        + cos(lat0) * sin(lon0) * dy
        + sin(lat0) * dz
    )
    return east, north, up


class GPSObservationAdapter:
    """Convert a GPS fix into an explicitly aligned model-frame observation."""

    def __init__(
        self,
        anchor: GeodeticAnchor,
        transform: CoordinateTransform,
        *,
        source_id: str = "gps",
    ) -> None:
        if transform.source_frame != anchor.frame_id:
            raise ValueError("transform source frame must match the GPS ENU anchor frame")
        if not source_id.strip():
            raise ValueError("source_id must not be empty")
        self.anchor = anchor
        self.transform = transform
        self.source_id = source_id

    def adapt(self, fix: GPSFix, model: BlueprintModel) -> SpatialObservation:
        if self.transform.target_frame != model.frame_id:
            raise ValueError("transform target frame must match active blueprint frame")
        enu = _to_enu(fix, self.anchor)
        model_position = self.transform.apply(enu, source_frame=self.anchor.frame_id)
        uncertainty = max(
            fix.horizontal_accuracy_m,
            fix.vertical_accuracy_m if fix.vertical_accuracy_m is not None
            else fix.horizontal_accuracy_m,
        )
        observation_id = fix.fix_id or f"gps-{fix.timestamp_ns}-{uuid4().hex[:8]}"
        return SpatialObservation(
            observation_id=observation_id,
            source_id=self.source_id,
            model_id=model.model_id,
            model_revision=model.revision,
            frame_id=model.frame_id,
            timestamp_ns=fix.timestamp_ns,
            position_m=model_position,
            uncertainty_m=uncertainty,
            provenance=(
                f"GPS WGS84 fix={observation_id}; "
                f"anchor={self.anchor.latitude_deg},{self.anchor.longitude_deg},"
                f"{self.anchor.altitude_m}; horizontal_accuracy_m={fix.horizontal_accuracy_m}; "
                f"vertical_accuracy_m={fix.vertical_accuracy_m}"
            ),
        )
