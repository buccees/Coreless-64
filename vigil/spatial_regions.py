"""Explicit, calibrated polygon regions for VIGIL spatial queries.

Regions are supplied in the same meter-based model frame as the active blueprint.
They are not inferred from a scanned image or from nearest-feature labels.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Sequence

from .blueprint import BlueprintModel, PoseEstimate, PoseState, _validate_vector
from .spatial_query import SpatialQueryStatus


@dataclass(frozen=True)
class SpatialRegion:
    region_id: str
    label: str
    model_id: str
    model_revision: str
    frame_id: str
    polygon_xy_m: tuple[tuple[float, float], ...]
    min_z_m: float
    max_z_m: float
    level: str | None = None
    zone: str | None = None

    def __post_init__(self) -> None:
        if not all(isinstance(value, str) and value.strip() for value in (
            self.region_id, self.label, self.model_id, self.model_revision, self.frame_id
        )):
            raise ValueError("region identity, label, model, revision, and frame are required")
        if self.level is not None and (not isinstance(self.level, str) or not self.level.strip()):
            raise ValueError("level must be a non-empty string or None")
        if self.zone is not None and (not isinstance(self.zone, str) or not self.zone.strip()):
            raise ValueError("zone must be a non-empty string or None")
        points = []
        try:
            for point in self.polygon_xy_m:
                if len(point) != 2 or not all(isfinite(float(value)) for value in point):
                    raise ValueError("region polygon vertices must be finite XY pairs")
                points.append((float(point[0]), float(point[1])))
        except (TypeError, OverflowError) as exc:
            raise ValueError("region polygon vertices must be finite XY pairs") from exc
        # Accept conventional closed rings, but store one canonical open ring.
        if len(points) >= 2 and points[0] == points[-1]:
            points.pop()
        if len(points) < 3:
            raise ValueError("region polygon requires at least three distinct vertices")
        if len(set(points)) != len(points):
            raise ValueError("region polygon must not repeat vertices")
        edge_epsilon = 1e-9
        for index, point in enumerate(points):
            nxt = points[(index + 1) % len(points)]
            if (point[0] - nxt[0]) ** 2 + (point[1] - nxt[1]) ** 2 <= edge_epsilon ** 2:
                raise ValueError("region polygon must not contain zero-length edges")
        def orientation(a, b, c):
            return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

        def on_segment(a, b, p):
            return (
                min(a[0], b[0]) - edge_epsilon <= p[0] <= max(a[0], b[0]) + edge_epsilon
                and min(a[1], b[1]) - edge_epsilon <= p[1] <= max(a[1], b[1]) + edge_epsilon
            )

        def intersects(a, b, d, e):
            o1, o2 = orientation(a, b, d), orientation(a, b, e)
            o3, o4 = orientation(d, e, a), orientation(d, e, b)
            proper = ((o1 > edge_epsilon and o2 < -edge_epsilon or o1 < -edge_epsilon and o2 > edge_epsilon)
                      and (o3 > edge_epsilon and o4 < -edge_epsilon or o3 < -edge_epsilon and o4 > edge_epsilon))
            if proper:
                return True
            return (
                abs(o1) <= edge_epsilon and on_segment(a, b, d)
                or abs(o2) <= edge_epsilon and on_segment(a, b, e)
                or abs(o3) <= edge_epsilon and on_segment(d, e, a)
                or abs(o4) <= edge_epsilon and on_segment(d, e, b)
            )

        count = len(points)
        for i in range(count):
            a, b = points[i], points[(i + 1) % count]
            for j in range(i + 1, count):
                # Neighboring polygon edges are expected to meet at their shared vertex.
                if j == i or j == (i + 1) % count or (j + 1) % count == i:
                    continue
                d, e = points[j], points[(j + 1) % count]
                if intersects(a, b, d, e):
                    raise ValueError("region polygon must not self-intersect")
        area_twice = sum(
            points[i][0] * points[(i + 1) % len(points)][1]
            - points[(i + 1) % len(points)][0] * points[i][1]
            for i in range(len(points))
        )
        if abs(area_twice) <= 1e-9:
            raise ValueError("region polygon must have non-zero area")
        object.__setattr__(self, "polygon_xy_m", tuple(points))
        if not isfinite(self.min_z_m) or not isfinite(self.max_z_m) or self.min_z_m > self.max_z_m:
            raise ValueError("region Z bounds must be finite and min_z_m <= max_z_m")

    def contains(self, position_m: Sequence[float], *, boundary_tolerance_m: float = 1e-9) -> bool:
        """Return whether a point lies inside/on the XY polygon and within Z bounds."""
        x, y, z = _validate_vector(position_m, "region query position")
        if not isfinite(boundary_tolerance_m) or boundary_tolerance_m < 0:
            raise ValueError("boundary_tolerance_m must be finite and non-negative")
        if z < self.min_z_m - boundary_tolerance_m or z > self.max_z_m + boundary_tolerance_m:
            return False
        points = self.polygon_xy_m
        inside = False
        for index, (x1, y1) in enumerate(points):
            x2, y2 = points[(index + 1) % len(points)]
            # Treat points on a segment as inside, with a small explicit tolerance.
            dx, dy = x2 - x1, y2 - y1
            length_sq = dx * dx + dy * dy
            if length_sq:
                t = min(1.0, max(0.0, ((x - x1) * dx + (y - y1) * dy) / length_sq))
                px, py = x1 + t * dx, y1 + t * dy
                if (x - px) ** 2 + (y - py) ** 2 <= boundary_tolerance_m ** 2:
                    return True
            if (y1 > y) != (y2 > y):
                crossing_x = x1 + (y - y1) * dx / dy
                if x < crossing_x:
                    inside = not inside
        return inside


@dataclass(frozen=True)
class RegionQueryResult:
    status: SpatialQueryStatus
    region_id: str
    evaluated_at_ns: int
    observation_timestamp_ns: int | None
    inside: bool | None
    position_m: tuple[float, float, float] | None
    uncertainty_m: float | None
    reason: str | None = None


def query_region(
    model: BlueprintModel,
    pose: PoseEstimate | None,
    region: SpatialRegion,
    *,
    now_ns: int,
    max_age_ns: int = 2_000_000_000,
    max_uncertainty_m: float = 5.0,
) -> RegionQueryResult:
    """Evaluate region membership without returning a false inside/outside on no-fix."""
    if not isinstance(model, BlueprintModel):
        raise TypeError("model must be a validated BlueprintModel")
    if not isinstance(region, SpatialRegion):
        raise TypeError("region must be a SpatialRegion")
    if isinstance(now_ns, bool) or not isinstance(now_ns, int) or now_ns < 0:
        raise ValueError("now_ns must be a non-negative integer")
    if isinstance(max_age_ns, bool) or not isinstance(max_age_ns, int) or max_age_ns < 0:
        raise ValueError("max_age_ns must be a non-negative integer")
    if not isfinite(max_uncertainty_m) or max_uncertainty_m < 0:
        raise ValueError("max_uncertainty_m must be finite and non-negative")

    timestamp = pose.observation_timestamp_ns if pose else None
    uncertainty = pose.uncertainty_m if pose else None

    def unavailable(status: SpatialQueryStatus, reason: str) -> RegionQueryResult:
        return RegionQueryResult(status, region.region_id, now_ns, timestamp, None, None, uncertainty, reason)

    if (region.model_id, region.model_revision, region.frame_id) != (
        model.model_id, model.revision, model.frame_id
    ):
        return unavailable(SpatialQueryStatus.MODEL_MISMATCH, "region does not match active model/revision/frame")
    if pose is None:
        return unavailable(SpatialQueryStatus.NO_FIX, "no pose estimate supplied")
    if (pose.model_id, pose.model_revision, pose.frame_id) != (
        model.model_id, model.revision, model.frame_id
    ):
        return unavailable(SpatialQueryStatus.MODEL_MISMATCH, "pose does not match active model/revision/frame")
    if pose.position_m is None or timestamp is None or pose.state in (
        PoseState.UNINITIALIZED, PoseState.CALIBRATING, PoseState.LOST
    ):
        return unavailable(SpatialQueryStatus.NO_FIX, pose.reason or "pose has no usable position fix")
    if timestamp > now_ns:
        return unavailable(SpatialQueryStatus.FUTURE_TIMESTAMP, "pose timestamp is later than query time")
    if now_ns - timestamp > max_age_ns:
        return unavailable(SpatialQueryStatus.STALE, "pose exceeds the configured maximum age")

    position = _validate_vector(pose.position_m, "pose position")
    status = (
        SpatialQueryStatus.OK
        if pose.state == PoseState.TRACKING and uncertainty is not None and uncertainty <= max_uncertainty_m
        else SpatialQueryStatus.DEGRADED
    )
    reason = None if status == SpatialQueryStatus.OK else (
        pose.reason or "pose state or uncertainty does not meet the configured quality threshold"
    )
    return RegionQueryResult(
        status, region.region_id, now_ns, timestamp,
        region.contains(position), position, uncertainty, reason,
    )
