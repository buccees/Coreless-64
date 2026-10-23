"""Optional, Coreless-native VIGIL environment."""

from .ai import AnalysisResult, CorelessVigilAI, OptionalAIAnalyzer
from .attention import AttentionItem, AttentionLifecycle, AttentionManager
from .blueprint_view import AxisBounds, BlueprintView, FeatureProjection, PoseProjection, build_blueprint_view
from .spatial_query import SpatialQueryEngine, SpatialQueryResult, SpatialQueryStatus
from .spatial_regions import RegionQueryResult, SpatialRegion, query_region
from .spatial_registry_store import SpatialRegistryStore
from .building import BuildingBlueprint, BuildingBlueprintBuilder, FloorRegistration, FloorTracker, FloorTransition, VerticalConnection
from .blueprint import (
    BlueprintModel,
    CoordinateTransform,
    ModelFeature,
    PoseEstimate,
    PoseState,
    load_blueprint_json,
    nearest_feature,
    register_blueprint,
)
from .input import VigilInputInterpreter, VigilInputLayer
from .positioning import FakeObservationProvider, PoseEstimator, SpatialObservation
from .gesture import GestureInterpreter, GestureResult, TouchPoint
from .gps import GPSFix, GPSObservationAdapter, GeodeticAnchor
from .terminal import SensorLine, VigilTerminal
from .workspace import BlueprintRegistry, PreloadedFloorWindow, SensorBatch, SensorPollStatus, SpatialSensorProvider, SpatialWorkspace, WorkspaceSnapshot
from .sensor_adapters import RangeMeasurement, acoustic_tof_range_m, rf_tof_range_m, to_object_observation, trilaterate_3d
from .raster_calibration import RasterBlueprintCalibration, RasterControlPoint
from .infrared_floor_mapping import InfraredFloorMap, InfraredFloorMapper, InfraredPixelSample, MappedInfraredSample
from .object_tracking import ObjectObservation, ObjectTrack, ObjectTracker, TrackingModality
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
from .visual_pointer import VisualPointer, VisualTouchIntent
from .fast_touch import FastCameraTouchPath, FastTouchDetector
from .camera import SharedCameraSource, CameraReader

__all__ = [
    "AnalysisResult", "AttentionItem", "AttentionLifecycle", "AttentionManager", "SpatialQueryEngine", "SpatialQueryResult", "SpatialQueryStatus", "SpatialRegion", "RegionQueryResult", "query_region", "SpatialRegistryStore",
    "AuthorizationContext", "AuthorizationService", "BlueprintModel", "BlueprintView", "BuildingBlueprint", "BuildingBlueprintBuilder", "FloorRegistration", "FloorTracker", "FloorTransition", "VerticalConnection", "AxisBounds", "CameraFrame",
    "CameraReader", "CoordinateTransform", "CorelessVigilAI", "Detection",
    "DetectionKind", "EntityType", "FeatureProjection", "PoseProjection", "FastCameraTouchPath", "FastTouchDetector",
    "FakeObservationProvider", "GPSFix", "GPSObservationAdapter", "GeodeticAnchor", "HumanInteractionService", "InteractionRequest", "InteractionResponse",
    "GestureInterpreter", "GestureResult", "ModelFeature", "Observation",
    "TouchPoint", "OptionalAIAnalyzer", "PoseEstimate", "PoseState", "PoseEstimator",
    "PresentationManager", "PresentationState", "PriorityContext", "PriorityResult",
    "Provenance", "RelevancePriorityEngine", "ReplayEvent", "ReplayLog",
    "ReplaySource", "ReplayValidation", "SensorState", "SharedCameraSource",
    "SimulationFrame", "SpatialPoint", "Track", "TrackManager", "Uncertainty",
    "SensorLine", "VigilTerminal", "BlueprintRegistry", "PreloadedFloorWindow", "SensorBatch", "SensorPollStatus", "SpatialSensorProvider", "SpatialWorkspace", "WorkspaceSnapshot",
    "RangeMeasurement", "acoustic_tof_range_m", "rf_tof_range_m", "to_object_observation", "trilaterate_3d",
    "RasterBlueprintCalibration", "RasterControlPoint", "InfraredFloorMap", "InfraredFloorMapper", "InfraredPixelSample", "MappedInfraredSample",
    "ObjectObservation", "ObjectTrack", "ObjectTracker", "TrackingModality",
    "VigilEnvironment", "VigilInputInterpreter", "VigilInputLayer", "VigilStatus",
    "VisualPointer", "VisualTouchIntent", "WorldEntity", "WorldModel",
    "WorldModelEvent", "bearing_degrees", "distance_between", "nearest_feature",
    "load_blueprint_json", "register_blueprint", "build_blueprint_view",
]

from .provenance import EventProvenance
from .simulation import ReplayEvent, ReplayLog, ReplayValidation
