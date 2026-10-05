"""Optional, Coreless-native VIGIL environment."""

from .attention import AttentionItem, AttentionLifecycle, AttentionManager
from .input import VigilInputInterpreter, VigilInputLayer
from .interaction import HumanInteractionService, InteractionRequest, InteractionResponse
from .model import Detection, EntityType, Observation, Provenance, SensorState, Track, Uncertainty, WorldEntity
from .priority import PriorityContext, PriorityResult, RelevancePriorityEngine
from .runtime import VigilEnvironment, VigilStatus
from .spatial import CameraFrame, DetectionKind, SpatialPoint
from .tracking import TrackManager
from .world import WorldModel, WorldModelEvent

__all__ = [
    "AttentionItem", "AttentionLifecycle", "AttentionManager",
    "CameraFrame", "Detection", "DetectionKind", "EntityType",
    "HumanInteractionService", "InteractionRequest", "InteractionResponse",
    "Observation", "PriorityContext", "PriorityResult", "Provenance",
    "RelevancePriorityEngine", "SensorState", "SpatialPoint", "Track",
    "TrackManager", "Uncertainty", "VigilEnvironment", "VigilInputInterpreter",
    "VigilInputLayer", "VigilStatus", "WorldEntity", "WorldModel", "WorldModelEvent",
]
