"""Blueprint registry and operator-facing spatial-scan workflow.

The workspace coordinates manifest import, active model/revision selection,
floor selection, observation ingestion, pose estimation, and terminal rendering.
It does not parse raw CAD/PDF files or own hardware sensor drivers.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from .blueprint import BlueprintModel, PoseEstimate, load_blueprint_json
from .blueprint_view import BlueprintView, build_blueprint_view
from .building import BuildingBlueprint, FloorTracker, FloorTransition
from .positioning import PoseEstimator, SpatialObservation
from .object_tracking import ObjectObservation, ObjectTrack, ObjectTracker, TrackingModality
from .terminal import VigilTerminal
from .infrared_floor_mapping import InfraredFloorMap


@dataclass(frozen=True)
class PreloadedFloorWindow:
    active_level: str
    below_level: str | None
    above_level: str | None
    loaded_levels: tuple[str, ...]
    views: tuple[BlueprintView, ...]


@dataclass(frozen=True)
class SensorBatch:
    """One sensor poll can contribute to pose, object tracks, and floor overlays."""

    position_observations: tuple[SpatialObservation, ...] = ()
    object_observations: tuple[ObjectObservation, ...] = ()
    infrared_maps: tuple[InfraredFloorMap, ...] = ()

    def __post_init__(self) -> None:
        if any(not isinstance(item, SpatialObservation) for item in self.position_observations):
            raise TypeError("position_observations must contain SpatialObservation values")
        if any(not isinstance(item, ObjectObservation) for item in self.object_observations):
            raise TypeError("object_observations must contain ObjectObservation values")
        if any(not isinstance(item, InfraredFloorMap) for item in self.infrared_maps):
            raise TypeError("infrared_maps must contain InfraredFloorMap values")


class SpatialSensorProvider(Protocol):
    """Optional adapter; legacy position-only sequences and SensorBatch are supported."""

    def read(self) -> Sequence[SpatialObservation] | SensorBatch:
        """Return calibrated model-frame data without mutating the workspace."""
        ...


@dataclass(frozen=True)
class SensorPollStatus:
    provider_id: str
    accepted: int
    state: str
    error: str | None = None


@dataclass(frozen=True)
class WorkspaceSnapshot:
    model: BlueprintModel | None
    pose: PoseEstimate | None
    selected_level: str | None
    observation_count: int
    floor_transition: FloorTransition | None = None
    object_tracks: tuple[ObjectTrack, ...] = ()
    infrared_maps: tuple[InfraredFloorMap, ...] = ()


class BlueprintRegistry:
    """In-memory registry keyed by model ID and revision."""

    def __init__(self) -> None:
        self._models: dict[tuple[str, str], BlueprintModel] = {}
        self._active_key: tuple[str, str] | None = None

    @property
    def active_model(self) -> BlueprintModel | None:
        return self._models.get(self._active_key) if self._active_key else None

    @property
    def models(self) -> tuple[BlueprintModel, ...]:
        return tuple(self._models[key] for key in sorted(self._models))

    def register(self, model: BlueprintModel, *, activate: bool = False) -> BlueprintModel:
        if not isinstance(model, BlueprintModel):
            raise TypeError("model must be a validated BlueprintModel")
        key = (model.model_id, model.revision)
        previous = self._models.get(key)
        if previous is not None and previous.source_sha256 != model.source_sha256:
            raise ValueError("model ID and revision already exist with different content")
        self._models[key] = model
        if activate or self._active_key is None:
            self._active_key = key
        return model

    def import_json(self, document: str | bytes, *, activate: bool = False,
                    max_bytes: int = 5_000_000) -> BlueprintModel:
        model = load_blueprint_json(document, max_bytes=max_bytes)
        return self.register(model, activate=activate)

    def activate(self, model_id: str, revision: str | None = None) -> BlueprintModel:
        matches = [
            key for key in self._models
            if key[0] == model_id and (revision is None or key[1] == revision)
        ]
        if not matches:
            raise KeyError(f"blueprint not registered: {model_id!r} revision={revision!r}")
        if revision is None and len(matches) > 1:
            raise ValueError("multiple revisions are registered; specify revision explicitly")
        key = matches[0]
        self._active_key = key
        return self._models[key]


class SpatialWorkspace:
    """Small deterministic API boundary for a blueprint scan session."""

    def __init__(
        self,
        *,
        registry: BlueprintRegistry | None = None,
        estimator: PoseEstimator | None = None,
        terminal: VigilTerminal | None = None,
        max_observations: int = 512,
    ) -> None:
        if max_observations < 1:
            raise ValueError("max_observations must be positive")
        self.registry = registry or BlueprintRegistry()
        self.estimator = estimator or PoseEstimator()
        self.terminal = terminal or VigilTerminal()
        self.max_observations = max_observations
        self._observations: list[SpatialObservation] = []
        self._pose: PoseEstimate | None = None
        self._selected_level: str | None = None
        self._floor_tracker: FloorTracker | None = None
        self._last_floor_pose_timestamp_ns: int | None = None
        self._last_floor_transition: FloorTransition | None = None
        self._building: BuildingBlueprint | None = None
        self._floor_views: dict[str, BlueprintView] = {}
        self.object_tracker = ObjectTracker()
        self._object_observations: list[ObjectObservation] = []
        self._object_tracks: tuple[ObjectTrack, ...] = ()
        self._infrared_maps: dict[str, InfraredFloorMap] = {}
        self._sensor_providers: dict[str, SpatialSensorProvider] = {}

    @property
    def active_model(self) -> BlueprintModel | None:
        return self.registry.active_model

    @property
    def selected_level(self) -> str | None:
        return self._selected_level

    @property
    def floor_transition(self) -> FloorTransition | None:
        return self._last_floor_transition

    @property
    def object_tracks(self) -> tuple[ObjectTrack, ...]:
        return self._object_tracks

    def activate_building(self, building: BuildingBlueprint, *, starting_level: str) -> BlueprintModel:
        """Activate a composed building and initialize automatic floor tracking."""
        model = self.registry.register(building.model, activate=True)
        self._pose = None
        self._selected_level = None
        self.object_tracker.clear()
        self._object_observations.clear()
        self._object_tracks = ()
        self._infrared_maps.clear()
        self._floor_tracker = FloorTracker(building)
        self._floor_tracker.establish_start(starting_level)
        self._building = building
        self._floor_views = {
            floor.level_id: build_blueprint_view(model, selected_level=floor.level_id)
            for floor in building.floors
        }
        self._selected_level = starting_level
        self._last_floor_pose_timestamp_ns = None
        self._last_floor_transition = FloorTransition(
            starting_level, None, False, "starting floor established"
        )
        return model

    def import_blueprint(self, document: str | bytes, *, activate: bool = False,
                         max_bytes: int = 5_000_000) -> BlueprintModel:
        previous_active = self.registry.active_model
        model = self.registry.import_json(document, activate=activate, max_bytes=max_bytes)
        if activate or previous_active is None:
            self._pose = None
            self._selected_level = None
            self._floor_tracker = None
            self.object_tracker.clear()
            self._object_observations.clear()
            self._object_tracks = ()
            self._infrared_maps.clear()
            self._building = None
            self._floor_views = {}
            self._last_floor_pose_timestamp_ns = None
            self._last_floor_transition = None
        return model

    def activate_blueprint(self, model_id: str, revision: str | None = None) -> BlueprintModel:
        model = self.registry.activate(model_id, revision)
        self._pose = None
        self._selected_level = None
        self._floor_tracker = None
        self.object_tracker.clear()
        self._object_observations.clear()
        self._object_tracks = ()
        self._infrared_maps.clear()
        self._building = None
        self._floor_views = {}
        self._last_floor_pose_timestamp_ns = None
        self._last_floor_transition = None
        return model

    def select_level(self, level: str) -> str:
        model = self.active_model
        if model is None:
            raise RuntimeError("register and activate a blueprint before selecting a level")
        normalized = level.strip()
        if not normalized:
            raise ValueError("level must not be empty")
        levels = {feature.level for feature in model.features if feature.level is not None}
        if normalized not in levels:
            raise KeyError(f"level not found in active blueprint: {normalized!r}")
        self._selected_level = normalized
        if self._floor_tracker is not None:
            # A manual floor choice resets the starting hypothesis; subsequent
            # transitions still require calibrated, repeated connector evidence.
            self._floor_tracker.establish_start(normalized)
            self._last_floor_pose_timestamp_ns = None
            self._last_floor_transition = FloorTransition(
                normalized, None, False, "starting floor reset manually"
            )
        return normalized

    def ingest(self, observations: Sequence[SpatialObservation]) -> int:
        """Append already-calibrated observations; returns accepted count.

        Observations are not transformed implicitly. Frame/revision alignment is
        enforced by PoseEstimator before any observation contributes to a pose.
        """
        accepted = 0
        for observation in observations:
            if not isinstance(observation, SpatialObservation):
                raise TypeError("all observations must be SpatialObservation instances")
            self._observations.append(observation)
            accepted += 1
        if len(self._observations) > self.max_observations:
            del self._observations[:-self.max_observations]
        return accepted

    def ingest_object_observations(self, observations: Sequence[ObjectObservation]) -> int:
        """Ingest detections already converted to calibrated model-frame positions."""
        accepted = 0
        for observation in observations:
            if not isinstance(observation, ObjectObservation):
                raise TypeError("all object observations must be ObjectObservation instances")
            self._object_observations.append(observation)
            accepted += 1
        if len(self._object_observations) > self.max_observations:
            del self._object_observations[:-self.max_observations]
        return accepted

    @property
    def infrared_maps(self) -> tuple[InfraredFloorMap, ...]:
        """Latest calibrated IR map per level, in deterministic level order."""
        return tuple(self._infrared_maps[key] for key in sorted(self._infrared_maps))

    def ingest_infrared_map(self, infrared_map: InfraredFloorMap, *, track_labeled_objects: bool = True) -> int:
        """Store a calibrated IR floor layer and forward labeled detections to tracking.

        IR pixels must already be calibrated into the active model frame. Unlabeled
        samples remain map evidence; infrared alone is not treated as a pose fix.
        """
        if not isinstance(infrared_map, InfraredFloorMap):
            raise TypeError("infrared_map must be an InfraredFloorMap")
        model = self.active_model
        if model is None:
            raise RuntimeError("activate a blueprint before ingesting infrared maps")
        if (infrared_map.model_id, infrared_map.model_revision, infrared_map.frame_id) != (
            model.model_id, model.revision, model.frame_id
        ):
            raise ValueError("infrared map must match the active model revision and frame")
        if self._building is not None and infrared_map.level_id not in {
            floor.level_id for floor in self._building.floors
        }:
            raise ValueError("infrared map level is not registered in the active building")
        self._infrared_maps[infrared_map.level_id] = infrared_map
        if not track_labeled_objects:
            return 0
        converted = []
        for sample in infrared_map.samples:
            if not sample.label.strip():
                continue
            converted.append(ObjectObservation(
                object_id=sample.label, sensor_id=sample.sensor_id,
                model_id=sample.model_id, model_revision=sample.model_revision,
                frame_id=sample.frame_id, timestamp_ns=sample.timestamp_ns,
                position_m=sample.position_m,
                uncertainty_m=max(sample.uncertainty_m, 0.01),
                modality=TrackingModality.INFRARED,
                provenance="calibrated-infrared-floor-map",
                association_id=sample.association_id,
            ))
        return self.ingest_object_observations(converted)

    @property
    def sensor_provider_ids(self) -> tuple[str, ...]:
        """Registered optional providers in deterministic order."""
        return tuple(sorted(self._sensor_providers))

    def register_sensor_provider(self, provider_id: str, provider: SpatialSensorProvider) -> None:
        """Register an optional adapter. Duplicate IDs are rejected, not overwritten."""
        if not isinstance(provider_id, str) or not provider_id.strip():
            raise ValueError("provider_id must not be empty")
        if not callable(getattr(provider, "read", None)):
            raise TypeError("sensor provider must implement read()")
        if provider_id in self._sensor_providers:
            raise ValueError(f"sensor provider already registered: {provider_id!r}")
        self._sensor_providers[provider_id] = provider

    def unregister_sensor_provider(self, provider_id: str) -> bool:
        """Remove an optional provider without affecting Coreless raw input."""
        return self._sensor_providers.pop(provider_id, None) is not None

    def poll_sensors(self) -> tuple[SensorPollStatus, ...]:
        """Poll optional providers independently; one faulty device cannot block others.

        Providers may return SensorBatch or a legacy position-only sequence. The
        workspace never assumes coordinates are correct: downstream estimators
        enforce active model/revision/frame alignment and observation freshness.
        Failures are returned as statuses rather than raised into the caller's
        input loop.
        """
        statuses: list[SensorPollStatus] = []
        for provider_id, provider in sorted(self._sensor_providers.items()):
            try:
                batch = provider.read()
                if isinstance(batch, SensorBatch):
                    accepted = self.ingest(batch.position_observations)
                    accepted += self.ingest_object_observations(batch.object_observations)
                    for infrared_map in batch.infrared_maps:
                        accepted += 1 + self.ingest_infrared_map(infrared_map)
                else:
                    # Backward compatibility for position-only providers.
                    if isinstance(batch, (str, bytes)) or not isinstance(batch, Sequence):
                        raise TypeError("read() must return SensorBatch or a sequence of SpatialObservation")
                    if any(not isinstance(item, SpatialObservation) for item in batch):
                        raise TypeError("read() returned a non-SpatialObservation item")
                    accepted = self.ingest(batch)
                statuses.append(SensorPollStatus(provider_id, accepted, "ONLINE"))
            except Exception as exc:
                # Adapter exceptions are contained at this optional boundary. The
                # caller can display this status; raw pointer/touch handling stays
                # outside this method and must never depend on provider health.
                message = " ".join(str(exc).split())[:180] or type(exc).__name__
                statuses.append(SensorPollStatus(provider_id, 0, "ERROR", message))
        return tuple(statuses)

    def refresh(self, *, now_ns: int, max_age_ns: int = 2_000_000_000,
                max_uncertainty_m: float = 5.0,
                max_disagreement_m: float = 2.0) -> WorkspaceSnapshot:
        model = self.active_model
        if model is None:
            self._pose = None
        else:
            self._pose = self.estimator.update(
                model, self._observations, now_ns=now_ns, max_age_ns=max_age_ns,
                max_uncertainty_m=max_uncertainty_m,
                max_disagreement_m=max_disagreement_m,
            )
            if self._floor_tracker is not None:
                timestamp = self._pose.observation_timestamp_ns
                pose_is_usable = (
                    self._pose.position_m is not None
                    and self._pose.uncertainty_m is not None
                    and self._pose.state.value in ("TRACKING", "DEGRADED")
                )
                # Repeated refreshes must not count one pose twice. Conversely,
                # an unavailable/stale pose must clear pending transition evidence.
                if not pose_is_usable or timestamp != self._last_floor_pose_timestamp_ns:
                    self._last_floor_transition = self._floor_tracker.update(self._pose)
                    self._last_floor_pose_timestamp_ns = timestamp
                    if self._last_floor_transition.changed:
                        self._selected_level = self._last_floor_transition.active_level
        if model is None:
            self._object_tracks = ()
        else:
            self._object_tracks = self.object_tracker.update(
                model, self._object_observations, now_ns=now_ns, max_age_ns=max_age_ns
            )
        return WorkspaceSnapshot(
            model, self._pose, self._selected_level, len(self._observations),
            self._last_floor_transition, self._object_tracks, self.infrared_maps,
        )

    def blueprint_view(
        self, *, now_ns: int, max_age_ns: int = 2_000_000_000,
        max_uncertainty_m: float = 5.0, max_disagreement_m: float = 2.0,
    ) -> BlueprintView:
        """Return geometry and pose overlay for the current selected floor."""
        snapshot = self.refresh(
            now_ns=now_ns, max_age_ns=max_age_ns,
            max_uncertainty_m=max_uncertainty_m,
            max_disagreement_m=max_disagreement_m,
        )
        if snapshot.model is None:
            raise RuntimeError("register and activate a blueprint before building its view")
        return build_blueprint_view(
            snapshot.model, snapshot.pose, selected_level=snapshot.selected_level,
            object_tracks=snapshot.object_tracks,
        )

    def preload_adjacent_floors(
        self, *, now_ns: int, max_age_ns: int = 2_000_000_000,
        max_uncertainty_m: float = 5.0, max_disagreement_m: float = 2.0,
    ) -> PreloadedFloorWindow:
        """Return ready-to-render active, immediately lower, and upper floor views.

        All registered floor geometry is prepared at building activation. This
        method exposes the active floor and its nearest vertical neighbors so a
        viewer can keep them mounted before a transition occurs.
        """
        if self._building is None or self._selected_level is None:
            raise RuntimeError("activate a connected building before preloading floor views")
        snapshot = self.refresh(
            now_ns=now_ns, max_age_ns=max_age_ns,
            max_uncertainty_m=max_uncertainty_m,
            max_disagreement_m=max_disagreement_m,
        )
        floors = sorted(self._building.floors, key=lambda floor: floor.elevation_m)
        active = next(floor for floor in floors if floor.level_id == self._selected_level)
        below = [floor for floor in floors if floor.elevation_m < active.elevation_m]
        above = [floor for floor in floors if floor.elevation_m > active.elevation_m]
        lower = below[-1] if below else None
        upper = above[0] if above else None
        selected = [floor for floor in (lower, active, upper) if floor is not None]
        views: list[BlueprintView] = []
        for floor in selected:
            # Geometry is precomputed, but live pose and object markers are rebuilt
            # on every window request so adjacent floors never display stale tracks.
            view = build_blueprint_view(
                snapshot.model, snapshot.pose if floor.level_id == self._selected_level else None,
                selected_level=floor.level_id, object_tracks=snapshot.object_tracks,
            )
            self._floor_views[floor.level_id] = view
            views.append(view)
        return PreloadedFloorWindow(
            active_level=self._selected_level,
            below_level=lower.level_id if lower else None,
            above_level=upper.level_id if upper else None,
            loaded_levels=tuple(floor.level_id for floor in selected),
            views=tuple(views),
        )

    def render(self, *, now_ns: int) -> str:
        snapshot = self.refresh(now_ns=now_ns)
        return self.terminal.render(
            snapshot.model, snapshot.pose, self._observations, now_ns=now_ns,
            selected_level=snapshot.selected_level,
            object_tracks=snapshot.object_tracks,
        )
