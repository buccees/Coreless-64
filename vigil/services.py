"""Deterministic spatial/environmental services over the World Model."""
from __future__ import annotations
from math import atan2, degrees, sqrt
from .model import WorldEntity


def distance_between(a: WorldEntity, b: WorldEntity) -> float | None:
    if a.position is None or b.position is None:
        return None
    return sqrt(sum((a.position[i] - b.position[i]) ** 2 for i in range(3)))


def bearing_degrees(origin: WorldEntity, target: WorldEntity) -> float | None:
    if origin.position is None or target.position is None:
        return None
    dx = target.position[0] - origin.position[0]
    dy = target.position[1] - origin.position[1]
    return (degrees(atan2(dy, dx)) + 360.0) % 360.0
