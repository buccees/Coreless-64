"""Blueprint registry and operator-facing spatial-scan workflow.

The workspace coordinates manifest import, active model/revision selection,
floor selection, observation ingestion, pose estimation, and terminal rendering.
It does not parse raw CAD/PDF files or own hardware sensor drivers.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Protocol, Sequence

from .blueprint import BlueprintModel, PoseEstimate, load_blueprint_json
from .blueprint_view import BlueprintView, build_blueprint_view
from .building import BuildingBlueprint, FloorTracker, FloorTransition
from .positioning import PoseEstimator, SpatialObservation
from .object_tracking import ObjectObservation, ObjectTrack, ObjectTracker, TrackingModality
from .terminal import VigilTerminal
from .infrared_floor_mapping import InfraredFloorMap, InfraredFloorMapper, InfraredPixelSample
from .spatial_scene import SpatialScene, assemble_spatial_scene
from .spatial_query import SpatialQueryEngine, SpatialQueryResult
from .spatial_regions import RegionQueryResult, SpatialRegion, query_region
from .spatial_registry_store import SpatialRegistryStore
from .sensor_mounts import SensorMountTransform


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
class ExpectedSensorCoverage:
    """Declared sensor expectation for explicit model regions."""
    sensor_id: str
    provider_id: str
    region_ids: tuple[str, ...]
    max_age_ns: int = 2_000_000_000


@dataclass(frozen=True)
class WorkspaceSnapshot:
    model: BlueprintModel | None
    pose: PoseEstimate | None
    selected_level: str | None
    observation_count: int
    floor_transition: FloorTransition | None = None
    object_tracks: tuple[ObjectTrack, ...] = ()
    infrared_maps: tuple[InfraredFloorMap, ...] = ()
    spatial_query: SpatialQueryResult | None = None
    region_results: tuple[RegionQueryResult, ...] = ()


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
        registry_store: SpatialRegistryStore | None = None,
    ) -> None:
        if max_observations < 1:
            raise ValueError("max_observations must be positive")
        self.registry = registry or BlueprintRegistry()
        self.registry_store = registry_store
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
        self._sensor_poll_statuses: tuple[SensorPollStatus, ...] = ()
        self._expected_sensor_coverage: dict[str, ExpectedSensorCoverage] = {}
        # Key by model/revision/region so activating an older blueprint cannot
        # silently reinterpret geometry registered for another revision.
        self._regions: dict[tuple[str, str, str], SpatialRegion] = {}
        # Restore the saved active model and regions when this workspace starts
        # with an empty in-memory registry. Sensor observations/poses stay transient.
        if self.registry_store is not None:
            active_ref = self.registry_store.active_model_ref
            if active_ref is not None:
                model_id, revision = active_ref
                restored = self.registry_store.load_model(model_id, revision)
                if restored is None:
                    raise ValueError("persistent active model points to a missing revision")
                if self.registry.active_model is None:
                    self.registry.register(restored, activate=True)
                active_model = self.registry.active_model
                if active_model is not None:
                    self._restore_regions(active_model)
                    self._restore_tracks(active_model)

    def _restore_regions(self, model: BlueprintModel) -> None:
        """Load persisted regions for this exact model/revision/frame."""
        if self.registry_store is None:
            return
        for region in self.registry_store.load_regions(model.model_id, model.revision):
            if (region.model_id, region.model_revision, region.frame_id) != (
                model.model_id, model.revision, model.frame_id
            ):
                raise ValueError("persisted spatial region does not match its model frame")
            self._regions[(region.model_id, region.model_revision, region.region_id)] = region

    def _restore_tracks(self, model: BlueprintModel) -> None:
        """Restore the last-known scene as non-current until fresh sensor input arrives."""
        if self.registry_store is None:
            return
        tracks = self.registry_store.load_object_tracks(model.model_id, model.revision)
        self._object_tracks = self.object_tracker.restore_tracks(tracks, model=model)

    def _persist_model(self, model: BlueprintModel, *, activate: bool) -> None:
        if self.registry_store is not None:
            self.registry_store.save_model(model, activate=activate)
            if not activate:
                return
        if self.registry_store is not None and activate:
            self.registry_store.set_active_model(model.model_id, model.revision)
            self._restore_regions(model)

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
        self._persist_model(building.model, activate=True)
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
        self._restore_tracks(model)
        return model

    def import_blueprint(self, document: str | bytes, *, activate: bool = False,
                         max_bytes: int = 5_000_000) -> BlueprintModel:
        previous_active = self.registry.active_model
        model = self.registry.import_json(document, activate=activate, max_bytes=max_bytes)
        becomes_active = activate or previous_active is None
        self._persist_model(model, activate=becomes_active)
        if self.registry_store is not None:
            source_bytes = document if isinstance(document, bytes) else document.encode("utf-8")
            self.registry_store.save_source_asset(
                model.model_id, model.revision, "source-manifest",
                asset_name="source-manifest.json", media_type="application/json",
                content=source_bytes,
                metadata={"source_format": "coreless-blueprint-json-v1"},
            )
        if becomes_active:
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
            self._restore_tracks(model)
        return model

    def activate_blueprint(self, model_id: str, revision: str | None = None) -> BlueprintModel:
        model = self.registry.activate(model_id, revision)
        self._persist_model(model, activate=True)
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
        self._restore_tracks(model)
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

    def ingest_sensor_local_object_observations(
        self, mount_id: str, observations: Sequence[ObjectObservation],
    ) -> int:
        """Transform explicitly sensor-local observations using a persisted mount.

        This separate entry point prevents accidentally transforming observations
        that an adapter has already expressed in the shared model frame.
        """
        if self.registry_store is None:
            raise RuntimeError("a persistent spatial registry is required to load sensor mounts")
        if not isinstance(mount_id, str) or not mount_id.strip():
            raise ValueError("mount_id is required")
        model = self.active_model
        if model is None:
            raise RuntimeError("activate a blueprint before ingesting sensor-local observations")
        mount = self.registry_store.load_sensor_mount(mount_id)
        if mount is None:
            raise KeyError(f"sensor mount is not registered: {mount_id}")
        if (mount.model_id, mount.model_revision, mount.frame_id) != (
            model.model_id, model.revision, model.frame_id
        ):
            raise ValueError("sensor mount must match the active model revision and frame")
        transformed = []
        for observation in observations:
            if not isinstance(observation, ObjectObservation):
                raise TypeError("all object observations must be ObjectObservation instances")
            if (observation.model_id, observation.model_revision, observation.frame_id) != (
                model.model_id, model.revision, mount.source_frame_id
            ):
                raise ValueError("sensor-local observation must match the mount source frame and active model revision")
            if observation.sensor_id != mount.sensor_id:
                raise ValueError("sensor-local observation sensor_id does not match the mount")
            status = "failed" if observation.calibration_status == "failed" else (
                "verified" if mount.verified else "unverified"
            )
            transformed.append(replace(
                observation,
                frame_id=mount.frame_id,
                position_m=mount.transform_position(observation.position_m),
                provenance=f"{observation.provenance};sensor-mount:{mount.mount_id}",
                calibration_status=status,
                calibration_ids=tuple(dict.fromkeys((*observation.calibration_ids, mount.mount_id))),
            ))
        return self.ingest_object_observations(transformed)

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

    def ingest_calibrated_infrared_pixels(
        self, calibration_id: str, *, sensor_id: str, sensor_mount_id: str,
        image_width: int, image_height: int,
        samples: Sequence[InfraredPixelSample], timestamp_ns: int,
        track_labeled_objects: bool = True,
    ) -> InfraredFloorMap:
        """Load a persisted raster calibration, map one pixel batch, and ingest it.

        sensor_mount_id is retained as provenance only. It does not imply that a
        physical mounting transform has been measured or applied; the saved raster
        calibration itself must already map this image into the model frame.
        """
        if self.registry_store is None:
            raise RuntimeError("a persistent spatial registry is required to load calibration")
        if not isinstance(calibration_id, str) or not calibration_id.strip():
            raise ValueError("calibration_id is required")
        if not isinstance(sensor_mount_id, str) or not sensor_mount_id.strip():
            raise ValueError("sensor_mount_id is required")
        model = self.active_model
        if model is None:
            raise RuntimeError("activate a blueprint before ingesting infrared pixels")
        calibration = self.registry_store.load_calibration(calibration_id)
        if calibration is None:
            raise KeyError(f"raster calibration is not registered: {calibration_id}")
        if (calibration.model_id, calibration.model_revision, calibration.frame_id) != (
            model.model_id, model.revision, model.frame_id
        ):
            raise ValueError("raster calibration must match the active model revision and frame")
        mapper = InfraredFloorMapper(
            calibration, sensor_id=sensor_id, image_width=image_width,
            image_height=image_height, calibration_id=calibration_id,
            sensor_mount_id=sensor_mount_id,
        )
        infrared_map = mapper.map_frame(samples, timestamp_ns=timestamp_ns)
        self.ingest_infrared_map(infrared_map, track_labeled_objects=track_labeled_objects)
        return infrared_map

    @property
    def spatial_regions(self) -> tuple[SpatialRegion, ...]:
        """Regions registered for the active model revision, sorted by ID."""
        model = self.active_model
        if model is None:
            return ()
        return tuple(sorted(
            (region for key, region in self._regions.items()
             if key[:2] == (model.model_id, model.revision)),
            key=lambda region: region.region_id,
        ))

    def register_region(self, region: SpatialRegion) -> SpatialRegion:
        """Register explicit calibrated geometry for the current model revision."""
        if not isinstance(region, SpatialRegion):
            raise TypeError("region must be a SpatialRegion")
        model = self.active_model
        if model is None:
            raise RuntimeError("activate a blueprint before registering spatial regions")
        if (region.model_id, region.model_revision, region.frame_id) != (
            model.model_id, model.revision, model.frame_id
        ):
            raise ValueError("region must match the active blueprint model, revision, and frame")
        key = (region.model_id, region.model_revision, region.region_id)
        if key in self._regions:
            raise ValueError(f"spatial region already registered: {region.region_id!r}")
        if self.registry_store is not None:
            self.registry_store.save_region(region)
        self._regions[key] = region
        return region

    def unregister_region(self, region_id: str) -> bool:
        """Remove a region from the active revision without touching other revisions."""
        model = self.active_model
        if model is None:
            return False
        key = (model.model_id, model.revision, region_id)
        existed = key in self._regions
        if self.registry_store is not None:
            persisted = self.registry_store.delete_region(model.model_id, model.revision, region_id)
            existed = existed or persisted
        self._regions.pop(key, None)
        return existed

    def query_region(
        self, region_id: str, *, now_ns: int,
        max_age_ns: int = 2_000_000_000, max_uncertainty_m: float = 5.0,
    ) -> RegionQueryResult:
        """Refresh the latest pose, then query one registered region safely."""
        model = self.active_model
        if model is None:
            raise RuntimeError("activate a blueprint before querying spatial regions")
        key = (model.model_id, model.revision, region_id)
        region = self._regions.get(key)
        if region is None:
            raise KeyError(f"spatial region not registered for active model: {region_id!r}")
        snapshot = self.refresh(
            now_ns=now_ns, max_age_ns=max_age_ns,
            max_uncertainty_m=max_uncertainty_m,
        )
        return query_region(
            model, snapshot.pose, region, now_ns=now_ns,
            max_age_ns=max_age_ns, max_uncertainty_m=max_uncertainty_m,
        )

    def query_spatial(
        self, *, now_ns: int, max_age_ns: int = 2_000_000_000,
        max_uncertainty_m: float = 5.0, nearby_radius_m: float | None = None,
    ) -> SpatialQueryResult | None:
        """Refresh and query model-relative nearest feature/zone status."""
        snapshot = self.refresh(
            now_ns=now_ns, max_age_ns=max_age_ns,
            max_uncertainty_m=max_uncertainty_m,
        )
        if snapshot.model is None:
            return None
        return SpatialQueryEngine(snapshot.model).evaluate(
            snapshot.pose, now_ns=now_ns, max_age_ns=max_age_ns,
            max_uncertainty_m=max_uncertainty_m,
            nearby_radius_m=nearby_radius_m,
        )

    @property
    def sensor_provider_ids(self) -> tuple[str, ...]:
        """Registered optional providers in deterministic order."""
        return tuple(sorted(self._sensor_providers))

    @property
    def sensor_poll_statuses(self) -> tuple[SensorPollStatus, ...]:
        """Most recent poll result for each provider; empty until the first poll."""
        return self._sensor_poll_statuses

    @property
    def expected_sensor_coverage(self) -> tuple[ExpectedSensorCoverage, ...]:
        return tuple(self._expected_sensor_coverage[key] for key in sorted(self._expected_sensor_coverage))

    def register_expected_sensor(self, sensor_id: str, *, provider_id: str, region_ids: Sequence[str], max_age_ns: int = 2_000_000_000) -> ExpectedSensorCoverage:
        """Declare where a sensor is expected to report; does not claim physical coverage."""
        if self.active_model is None:
            raise RuntimeError("activate a blueprint before declaring expected sensor coverage")
        if not isinstance(sensor_id, str) or not sensor_id.strip() or not isinstance(provider_id, str) or not provider_id.strip():
            raise ValueError("sensor_id and provider_id must not be empty")
        if isinstance(max_age_ns, bool) or not isinstance(max_age_ns, int) or max_age_ns < 0:
            raise ValueError("max_age_ns must be a non-negative integer")
        normalized = tuple(sorted(set(region_ids)))
        if not normalized:
            raise ValueError("at least one explicit region_id is required")
        unknown = set(normalized) - {region.region_id for region in self.spatial_regions}
        if unknown:
            raise KeyError(f"expected sensor references unknown regions: {sorted(unknown)!r}")
        if sensor_id in self._expected_sensor_coverage:
            raise ValueError(f"expected sensor already registered: {sensor_id!r}")
        expected = ExpectedSensorCoverage(sensor_id, provider_id, normalized, max_age_ns)
        self._expected_sensor_coverage[sensor_id] = expected
        return expected

    def unregister_expected_sensor(self, sensor_id: str) -> bool:
        return self._expected_sensor_coverage.pop(sensor_id, None) is not None

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
        self._sensor_poll_statuses = tuple(statuses)
        return self._sensor_poll_statuses

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
                model, self._object_observations, now_ns=now_ns,
                max_age_ns=max_age_ns, retain_stale=True,
            )
            if self.registry_store is not None:
                self.registry_store.save_object_tracks(model, self._object_tracks)
        spatial_query_result = (
            SpatialQueryEngine(model).evaluate(
                self._pose, now_ns=now_ns, max_age_ns=max_age_ns,
                max_uncertainty_m=max_uncertainty_m,
            )
            if model is not None else None
        )
        region_results = tuple(
            query_region(
                model, self._pose, region, now_ns=now_ns,
                max_age_ns=max_age_ns, max_uncertainty_m=max_uncertainty_m,
            )
            for region in self.spatial_regions
        ) if model is not None else ()
        return WorkspaceSnapshot(
            model, self._pose, self._selected_level, len(self._observations),
            self._last_floor_transition, self._object_tracks, self.infrared_maps,
            spatial_query_result, region_results,
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

    def spatial_scene(self, *, now_ns: int, max_age_ns: int = 2_000_000_000,
                      max_pose_uncertainty_m: float = 2.0) -> SpatialScene:
        """Assemble a quality-gated renderer scene from the latest workspace state."""
        snapshot = self.refresh(now_ns=now_ns, max_age_ns=max_age_ns)
        return assemble_spatial_scene(
            snapshot.model, snapshot.pose, snapshot.object_tracks, snapshot.infrared_maps,
            selected_level=snapshot.selected_level, now_ns=now_ns,
            max_pose_age_ns=max_age_ns, max_object_age_ns=max_age_ns,
            max_pose_uncertainty_m=max_pose_uncertainty_m,
        )

    def render(self, *, now_ns: int) -> str:
        snapshot = self.refresh(now_ns=now_ns)
        scene = assemble_spatial_scene(
            snapshot.model, snapshot.pose, snapshot.object_tracks, snapshot.infrared_maps,
            selected_level=snapshot.selected_level, now_ns=now_ns,
        )
        return self.terminal.render(
            snapshot.model, snapshot.pose, self._observations, now_ns=now_ns,
            selected_level=snapshot.selected_level,
            object_tracks=snapshot.object_tracks,
            spatial_scene=scene,
            spatial_query=snapshot.spatial_query,
            region_results=snapshot.region_results,
        )
