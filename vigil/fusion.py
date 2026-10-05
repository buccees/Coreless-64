"""Deterministic spatial/temporal fusion foundation."""
from __future__ import annotations
from math import sqrt
from .model import Detection, Uncertainty


def distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return sqrt(sum((left - right) ** 2 for left, right in zip(a, b)))


def fuse_positions(
    detections: tuple[Detection, ...],
    *,
    max_distance: float | None = None,
) -> tuple[float, float, float] | None:
    positioned = [item for item in detections if item.position is not None]
    if not positioned:
        return None
    if max_distance is not None:
        anchor = positioned[0].position
        positioned = [item for item in positioned if distance(anchor, item.position) <= max_distance]
    weights = [max(item.confidence, 1e-9) for item in positioned]
    total = sum(weights)
    return tuple(
        sum(item.position[index] * weight for item, weight in zip(positioned, weights)) / total
        for index in range(3)
    )


def fuse_uncertainty(detections: tuple[Detection, ...]) -> Uncertainty:
    values = [item.uncertainty.position_m for item in detections if item.uncertainty.position_m is not None]
    return Uncertainty(position_m=min(values) if values else None)
