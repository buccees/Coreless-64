"""Optional VIGIL spatial-input intelligence layer for Coreless-64."""

from .input import VigilInputLayer, VigilInputInterpreter
from .spatial import CameraFrame, Observation, Detection, Track, SpatialPoint

__all__ = [
    "CameraFrame",
    "Detection",
    "Observation",
    "SpatialPoint",
    "Track",
    "VigilInputInterpreter",
    "VigilInputLayer",
]
