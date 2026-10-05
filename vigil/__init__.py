"""Optional, Coreless-native VIGIL environment."""

from .ai import AnalysisResult, OptionalAIAnalyzer
from .attention import AttentionItem, AttentionLifecycle, AttentionManager
from .input import VigilInputInterpreter, VigilInputLayer
from .interaction import HumanInteractionService, InteractionRequest, InteractionResponse
from .model import Detection, EntityType, Observation, Provenance, SensorState, Track, Uncertainty, WorldEntity
from .presentation import PresentationManager, PresentationState
from .perception import PerceptionPipeline, PerceptionResult, detection_from_observation
from .priority import PriorityContext, PriorityResult, RelevancePriorityEngine
from .runtime import VigilEnvironment, VigilStatus
from .security import AuthorizationContext, AuthorizationService
from .services import bearing_degrees, distance_between
from .simulation import ReplaySource, SimulationFrame
from .spatial import CameraFrame, DetectionKind, SpatialPoint
from .tracking import TrackManager
from .world import WorldModel, WorldModelEvent

__all__ = [
    "AnalysisResult", "AttentionItem", "AttentionLifecycle", "AttentionManager",
    "AuthorizationContext", "AuthorizationService", "CameraFrame", "Detection",
    "DetectionKind", "EntityType", "HumanInteractionService", "InteractionRequest",
    "InteractionResponse", "Observation", "OptionalAIAnalyzer", "PresentationManager",
    "PresentationState", "PriorityContext", "PriorityResult", "Provenance",
    "RelevancePriorityEngine", "ReplaySource", "SensorState", "SimulationFrame",
    "SpatialPoint", "Track", "TrackManager", "Uncertainty", "VigilEnvironment",
    "VigilInputInterpreter", "VigilInputLayer", "VigilStatus", "WorldEntity",
    "WorldModel", "WorldModelEvent", "bearing_degrees", "distance_between",
]
