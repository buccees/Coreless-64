import json

import pytest

from vigil.blueprint import register_blueprint
from vigil.positioning import SpatialObservation
from vigil.terminal import VigilTerminal
from vigil.workspace import BlueprintRegistry, SpatialWorkspace


def manifest(model_id="site-a", revision="r1", level="L1"):
    return json.dumps({
        "schema_version": 1, "model_id": model_id, "revision": revision,
        "frame_id": f"{model_id}/local", "units": "m",
        "features": [
            {"feature_id": "anchor", "label": "Anchor", "position": [0, 0, 0],
             "level": level, "zone": "north"},
            {"feature_id": "lift", "label": "Lift", "position": [4, 0, 0],
             "level": "L2", "zone": "core"},
        ],
    })


def observation(model, source, x=0.2, timestamp=100):
    return SpatialObservation(
        f"obs-{source}", source, model.model_id, model.revision, model.frame_id,
        timestamp, (x, 0, 0), 0.2, "workspace-test",
    )


def test_registry_imports_and_activates_manifest():
    registry = BlueprintRegistry()
    first = registry.import_json(manifest())
    second = registry.import_json(manifest("site-b", "r2"), activate=True)
    assert first.model_id == "site-a"
    assert registry.active_model == second
    assert len(registry.models) == 2


def test_registry_requires_revision_when_model_has_multiple_revisions():
    registry = BlueprintRegistry()
    registry.register(register_blueprint(
        "site", "r1", frame_id="site/local", units="m",
        features=[{"feature_id": "a", "label": "A", "position": [0, 0, 0]}],
    ))
    registry.register(register_blueprint(
        "site", "r2", frame_id="site/local", units="m",
        features=[{"feature_id": "a", "label": "A", "position": [1, 0, 0]}],
    ))
    with pytest.raises(ValueError, match="specify revision"):
        registry.activate("site")
    assert registry.activate("site", "r2").revision == "r2"


def test_workspace_selects_level_and_fuses_aligned_observations():
    workspace = SpatialWorkspace(terminal=VigilTerminal(color=False))
    model = workspace.import_blueprint(manifest(), activate=True)
    assert workspace.select_level("L1") == "L1"
    assert workspace.ingest([observation(model, "uwb"), observation(model, "vision", 0.25)]) == 2
    snapshot = workspace.refresh(now_ns=110)
    assert snapshot.model == model
    assert snapshot.selected_level == "L1"
    assert snapshot.pose is not None
    assert snapshot.pose.position_m is not None
    assert snapshot.pose.state.value == "TRACKING"
    rendered = workspace.render(now_ns=110)
    assert "L1" in rendered
    assert "TRACKING" in rendered


def test_workspace_shows_lost_when_no_fresh_observations():
    workspace = SpatialWorkspace(terminal=VigilTerminal(color=False))
    workspace.import_blueprint(manifest(), activate=True)
    snapshot = workspace.refresh(now_ns=10)
    assert snapshot.pose is not None
    assert snapshot.pose.position_m is None
    assert snapshot.pose.state.value == "LOST"


def test_workspace_rejects_unknown_level_and_does_not_transform_inputs():
    workspace = SpatialWorkspace()
    model = workspace.import_blueprint(manifest(), activate=True)
    with pytest.raises(KeyError, match="level not found"):
        workspace.select_level("L99")
    wrong_frame = SpatialObservation(
        "wrong", "uwb", model.model_id, model.revision, "device-frame", 100,
        (0, 0, 0), 0.2, "test",
    )
    workspace.ingest([wrong_frame])
    pose = workspace.refresh(now_ns=110).pose
    assert pose is not None and pose.position_m is None


def test_workspace_activates_building_tracks_floor_and_builds_selected_floor_view():
    from vigil.blueprint import CoordinateTransform
    from vigil.building import BuildingBlueprintBuilder, VerticalConnection

    lower = register_blueprint(
        "upload-lower", "r1", frame_id="lower/local", units="m",
        features=[
            {"feature_id": "entry", "label": "Entry", "position": [0, 0, 0]},
            {"feature_id": "stairs", "label": "Stairs", "position": [5, 5, 0]},
        ],
    )
    upper = register_blueprint(
        "upload-upper", "r1", frame_id="upper/local", units="m",
        features=[
            {"feature_id": "stairs", "label": "Stairs", "position": [0, 0, 0]},
            {"feature_id": "office", "label": "Office", "position": [3, 2, 0]},
        ],
    )
    builder = BuildingBlueprintBuilder("building", "r1", "building/world")
    builder.add_floor(
        lower, level_id="L1", label="Ground", elevation_m=0,
        transform_to_building=CoordinateTransform(
            "lower/local", "building/world", translation=(0, 0, 0), provenance="survey"
        ),
    )
    builder.add_floor(
        upper, level_id="L2", label="Upper", elevation_m=3,
        transform_to_building=CoordinateTransform(
            "upper/local", "building/world", translation=(5, 5, 3), provenance="survey"
        ),
    )
    builder.connect_floors(VerticalConnection(
        "stairs", "stairs", "L1", "L2", (5, 5, 0), (5, 5, 3)
    ))
    building = builder.build()

    workspace = SpatialWorkspace(terminal=VigilTerminal(color=False))
    workspace.activate_building(building, starting_level="L1")
    assert workspace.selected_level == "L1"
    assert len(workspace.blueprint_view(now_ns=1).features) == 2

    for timestamp in (100, 200):
        workspace.ingest([SpatialObservation(
            f"upper-{timestamp}", "uwb", building.model.model_id,
            building.model.revision, building.model.frame_id, timestamp,
            (5, 5, 3), 0.2, "calibrated-building-frame",
        )])
        snapshot = workspace.refresh(now_ns=timestamp, max_age_ns=50)
    assert snapshot.floor_transition is not None
    assert snapshot.floor_transition.changed
    assert workspace.selected_level == "L2"
    view = workspace.blueprint_view(now_ns=200, max_age_ns=50)
    assert view.selected_level == "L2"
    assert {feature.level for feature in view.features} == {"L2"}
    assert view.pose is not None
    assert workspace.select_level("L1") == "L1"
    assert workspace.floor_transition is not None
    assert workspace.floor_transition.reason == "starting floor reset manually"



def test_workspace_preloads_active_and_immediately_adjacent_floor_views():
    from vigil.blueprint import CoordinateTransform
    from vigil.building import BuildingBlueprintBuilder

    builder = BuildingBlueprintBuilder("tower", "r1", "tower/world")
    for level, elevation in (("L1", 0.0), ("L2", 3.0), ("L3", 6.0)):
        frame = f"{level}/local"
        floor_model = register_blueprint(
            f"upload-{level}", "r1", frame_id=frame, units="m",
            features=[
                {"feature_id": "anchor", "label": f"{level} anchor",
                 "position": [0, 0, 0]},
                {"feature_id": "lift", "label": f"{level} lift",
                 "position": [2, 2, 0]},
            ],
        )
        builder.add_floor(
            floor_model, level_id=level, label=f"Floor {level}", elevation_m=elevation,
            transform_to_building=CoordinateTransform(
                frame, "tower/world", translation=(0, 0, elevation), provenance="survey"
            ),
        )
    building = builder.build()
    workspace = SpatialWorkspace()
    workspace.activate_building(building, starting_level="L2")

    window = workspace.preload_adjacent_floors(now_ns=10)
    assert window.active_level == "L2"
    assert window.below_level == "L1"
    assert window.above_level == "L3"
    assert window.loaded_levels == ("L1", "L2", "L3")
    assert len(window.views) == 3
    assert [view.selected_level for view in window.views] == ["L1", "L2", "L3"]
    assert all(view.features for view in window.views)


def test_workspace_requires_building_before_adjacent_floor_preload():
    workspace = SpatialWorkspace()
    with pytest.raises(RuntimeError, match="connected building"):
        workspace.preload_adjacent_floors(now_ns=0)



def test_workspace_exposes_live_object_tracks_from_calibrated_sensor_observations():
    from vigil.object_tracking import ObjectObservation, TrackingModality

    workspace = SpatialWorkspace()
    model = workspace.import_blueprint(manifest(), activate=True)
    workspace.ingest_object_observations([ObjectObservation(
        "worker-7", "rf-ranging-node", model.model_id, model.revision, model.frame_id,
        100, (1.0, 2.0, 0.0), 0.3, TrackingModality.RF_2_4_GHZ,
        "calibrated-2.4ghz-ranging-adapter",
    )])
    snapshot = workspace.refresh(now_ns=110)
    assert len(snapshot.object_tracks) == 1
    assert snapshot.object_tracks[0].object_id == "worker-7"
    assert snapshot.object_tracks[0].modalities == ("rf_2_4ghz",)
    assert workspace.object_tracks == snapshot.object_tracks

    workspace.activate_blueprint(model.model_id, model.revision)
    assert workspace.object_tracks == ()


def test_optional_sensor_providers_are_polled_independently_and_fail_open():
    class Provider:
        def __init__(self, batch=None, error=None):
            self.batch = batch
            self.error = error

        def read(self):
            if self.error:
                raise RuntimeError(self.error)
            return self.batch

    workspace = SpatialWorkspace()
    model = workspace.import_blueprint(manifest(), activate=True)
    workspace.register_sensor_provider("gps-primary", Provider([observation(model, "gps", x=1.25)]))
    workspace.register_sensor_provider("broken-camera", Provider(error="camera disconnected"))
    workspace.register_sensor_provider("wrong-payload", Provider([object()]))

    statuses = workspace.poll_sensors()
    assert workspace.sensor_poll_statuses == statuses
    by_id = {status.provider_id: status for status in statuses}
    assert tuple(by_id) == ("broken-camera", "gps-primary", "wrong-payload")
    assert by_id["gps-primary"].state == "ONLINE"
    assert by_id["gps-primary"].accepted == 1
    assert by_id["broken-camera"].state == "ERROR"
    assert "camera disconnected" in by_id["broken-camera"].error
    assert by_id["wrong-payload"].state == "ERROR"
    assert workspace.refresh(now_ns=110).pose.position_m == pytest.approx((1.25, 0, 0))


def test_sensor_provider_registration_is_explicit_and_removable():
    class Provider:
        def read(self):
            return ()

    workspace = SpatialWorkspace()
    provider = Provider()
    workspace.register_sensor_provider("imu", provider)
    with pytest.raises(ValueError, match="already registered"):
        workspace.register_sensor_provider("imu", provider)
    assert workspace.sensor_provider_ids == ("imu",)
    assert workspace.unregister_sensor_provider("imu")
    assert not workspace.unregister_sensor_provider("imu")
    assert workspace.sensor_provider_ids == ()

def test_unified_sensor_batch_feeds_pose_and_shared_object_tracker():
    from vigil.object_tracking import ObjectObservation, TrackingModality
    from vigil.workspace import SensorBatch

    class Provider:
        def read(self):
            return SensorBatch(
                position_observations=(observation(model, "uwb", x=1.0, timestamp=100),),
                object_observations=(ObjectObservation(
                    "cart-2", "vision-1", model.model_id, model.revision, model.frame_id,
                    100, (2.0, 1.0, 0.0), 0.25, TrackingModality.VISION,
                    "calibrated-vision-detection",
                ),),
            )

    workspace = SpatialWorkspace()
    model = workspace.import_blueprint(manifest(), activate=True)
    workspace.register_sensor_provider("combined-sensor-rig", Provider())
    statuses = workspace.poll_sensors()
    assert len(statuses) == 1 and statuses[0].state == "ONLINE"
    assert statuses[0].accepted == 2
    snapshot = workspace.refresh(now_ns=110)
    assert snapshot.pose is not None
    assert snapshot.pose.position_m == pytest.approx((1.0, 0.0, 0.0))
    assert len(snapshot.object_tracks) == 1
    assert snapshot.object_tracks[0].object_id == "cart-2"
    assert snapshot.object_tracks[0].modalities == ("vision",)


def test_failed_multimodal_provider_does_not_block_healthy_provider():
    from vigil.object_tracking import ObjectObservation, TrackingModality
    from vigil.workspace import SensorBatch

    class Provider:
        def __init__(self, batch=None, fail=False):
            self.batch, self.fail = batch, fail
        def read(self):
            if self.fail:
                raise RuntimeError("sensor offline")
            return self.batch

    workspace = SpatialWorkspace()
    model = workspace.import_blueprint(manifest(), activate=True)
    workspace.register_sensor_provider("broken", Provider(fail=True))
    workspace.register_sensor_provider("healthy", Provider(SensorBatch(
        object_observations=(ObjectObservation(
            "person-1", "uwb", model.model_id, model.revision, model.frame_id,
            100, (0.5, 0.5, 0.0), 0.3, TrackingModality.UWB, "test-adapter",
        ),)
    )))
    statuses = {item.provider_id: item for item in workspace.poll_sensors()}
    assert statuses["broken"].state == "ERROR"
    assert statuses["healthy"].state == "ONLINE"
    assert workspace.refresh(now_ns=100).object_tracks[0].object_id == "person-1"



def test_workspace_blueprint_view_includes_current_object_markers():
    from vigil.object_tracking import ObjectObservation, TrackingModality

    workspace = SpatialWorkspace()
    model = workspace.import_blueprint(manifest(), activate=True)
    workspace.select_level("L1")
    workspace.ingest_object_observations([ObjectObservation(
        "cart-9", "vision-camera", model.model_id, model.revision, model.frame_id,
        100, (2.0, 1.0, 0.0), 0.2, TrackingModality.VISION, "calibrated-camera",
    )])
    view = workspace.blueprint_view(now_ns=110)
    assert len(view.objects) == 1
    assert view.objects[0].object_id == "cart-9"
    assert view.objects[0].modalities == ("vision",)

def test_workspace_exposes_spatial_query_and_registered_region_membership():
    from vigil.spatial_regions import SpatialRegion

    workspace = SpatialWorkspace(terminal=VigilTerminal(color=False))
    model = workspace.import_blueprint(manifest(), activate=True)
    workspace.select_level("L1")
    region = SpatialRegion(
        "north-zone", "North zone", model.model_id, model.revision, model.frame_id,
        ((-1, -1), (2, -1), (2, 1), (-1, 1)),
        min_z_m=-1, max_z_m=1, level="L1", zone="north",
    )
    workspace.register_region(region)
    assert workspace.spatial_regions == (region,)
    workspace.ingest([
        observation(model, "uwb", x=0.2),
        observation(model, "vision", x=0.25),
    ])

    snapshot = workspace.refresh(now_ns=110)
    assert snapshot.spatial_query is not None
    assert snapshot.spatial_query.status.value == "OK"
    assert snapshot.spatial_query.nearest_feature_id == "anchor"
    assert len(snapshot.region_results) == 1
    assert snapshot.region_results[0].region_id == "north-zone"
    assert snapshot.region_results[0].inside is True
    assert workspace.query_spatial(now_ns=110).status.value == "OK"
    assert workspace.query_region("north-zone", now_ns=110).inside is True

    rendered = workspace.render(now_ns=110)
    assert "SPATIAL QUERY" in rendered
    assert "SPATIAL REGIONS" in rendered
    assert "north-zone: INSIDE [OK]" in rendered


def test_workspace_does_not_reinterpret_regions_for_another_revision():
    from vigil.spatial_regions import SpatialRegion

    workspace = SpatialWorkspace()
    model = workspace.import_blueprint(manifest(), activate=True)
    region = SpatialRegion(
        "north-zone", "North zone", model.model_id, model.revision, model.frame_id,
        ((0, 0), (1, 0), (1, 1), (0, 1)), min_z_m=0, max_z_m=1,
    )
    workspace.register_region(region)
    other = workspace.import_blueprint(manifest(model_id="site-b", revision="r2"), activate=True)
    assert workspace.spatial_regions == ()
    assert workspace.refresh(now_ns=100).region_results == ()
    with pytest.raises(KeyError, match="not registered"):
        workspace.query_region("north-zone", now_ns=100)
    assert other.model_id == "site-b"


def test_workspace_keeps_region_membership_unknown_without_a_valid_pose():
    from vigil.spatial_regions import SpatialRegion

    workspace = SpatialWorkspace()
    model = workspace.import_blueprint(manifest(), activate=True)
    workspace.register_region(SpatialRegion(
        "north-zone", "North zone", model.model_id, model.revision, model.frame_id,
        ((-1, -1), (2, -1), (2, 1), (-1, 1)),
        min_z_m=-1, max_z_m=1,
    ))
    snapshot = workspace.refresh(now_ns=100)
    assert snapshot.spatial_query is not None
    assert snapshot.spatial_query.status.value == "NO_FIX"
    assert snapshot.region_results[0].inside is None

def test_workspace_persists_active_model_and_regions_across_restart(tmp_path):
    from vigil.spatial_regions import SpatialRegion
    from vigil.spatial_registry_store import SpatialRegistryStore

    database = str(tmp_path / "vigil-spatial.sqlite3")
    first_store = SpatialRegistryStore(database)
    first = SpatialWorkspace(registry_store=first_store)
    model = first.import_blueprint(manifest(), activate=True)
    region = SpatialRegion(
        "north-zone", "North zone", model.model_id, model.revision, model.frame_id,
        ((-1, -1), (2, -1), (2, 1), (-1, 1)),
        min_z_m=-1, max_z_m=1, level="L1", zone="north",
    )
    first.register_region(region)
    assert first_store.active_model_ref == (model.model_id, model.revision)
    first_store.close()

    restored_store = SpatialRegistryStore(database)
    try:
        restored = SpatialWorkspace(registry_store=restored_store)
        assert restored.active_model == model
        assert restored.spatial_regions == (region,)
        snapshot = restored.refresh(now_ns=110)
        assert snapshot.spatial_query is not None
        assert snapshot.spatial_query.status.value == "NO_FIX"
        assert snapshot.region_results[0].inside is None
        assert restored.unregister_region("north-zone")
        assert restored.spatial_regions == ()
    finally:
        restored_store.close()


def test_workspace_persistent_activation_follows_explicit_revision_change(tmp_path):
    from vigil.spatial_registry_store import SpatialRegistryStore

    database = str(tmp_path / "vigil-spatial.sqlite3")
    store = SpatialRegistryStore(database)
    try:
        workspace = SpatialWorkspace(registry_store=store)
        first = workspace.import_blueprint(manifest("site-a", "r1"), activate=True)
        second = workspace.import_blueprint(manifest("site-a", "r2"), activate=False)
        assert workspace.active_model == first
        workspace.activate_blueprint("site-a", "r2")
        assert workspace.active_model == second
        assert store.active_model_ref == ("site-a", "r2")
    finally:
        store.close()

def test_workspace_keeps_stale_object_as_last_known_without_claiming_motion_or_departure():
    from vigil.object_tracking import ObjectObservation, TrackingModality

    workspace = SpatialWorkspace()
    model = workspace.import_blueprint(manifest(), activate=True)
    workspace.ingest_object_observations([ObjectObservation(
        "stationary-toolbox", "uwb-1", model.model_id, model.revision,
        model.frame_id, 100, (1.0, 2.0, 0.0), 0.2,
        TrackingModality.UWB, "calibrated-uwb",
    )])
    current = workspace.refresh(now_ns=110)
    assert current.object_tracks[0].presence_state == "TRACKING"

    stale = workspace.refresh(now_ns=3_000_000_000)
    assert len(stale.object_tracks) == 1
    assert stale.object_tracks[0].object_id == "stationary-toolbox"
    assert stale.object_tracks[0].presence_state == "STALE"
    assert stale.object_tracks[0].position_m == (1.0, 2.0, 0.0)
    assert stale.object_tracks[0].last_seen_ns == 100

    view = workspace.blueprint_view(now_ns=3_000_000_001)
    marker = next(item for item in view.objects if item.object_id == "stationary-toolbox")
    assert marker.presence_state == "STALE"
    assert marker.motion_state == "UNKNOWN"



def test_workspace_restores_persisted_object_as_reacquire_not_live():
    from vigil.object_tracking import ObjectObservation, TrackingModality
    from vigil.spatial_registry_store import SpatialRegistryStore

    store = SpatialRegistryStore()
    try:
        first = SpatialWorkspace(registry_store=store)
        active = first.import_blueprint(manifest(), activate=True)
        first.ingest_object_observations([ObjectObservation(
            "cart-7", "uwb-array", active.model_id, active.revision,
            active.frame_id, 100, (2.0, 3.0, 0.0), 0.2,
            TrackingModality.UWB, "calibrated-ranging",
            calibration_status="verified", calibration_ids=("survey-1",),
            lineage_declared=True,
        )])
        first.refresh(now_ns=100)

        restarted = SpatialWorkspace(registry_store=store)
        assert restarted.active_model == active
        assert len(restarted.object_tracks) == 1
        assert restarted.object_tracks[0].presence_state == "REACQUIRE"
        refreshed = restarted.refresh(now_ns=110)
        assert refreshed.object_tracks[0].presence_state == "REACQUIRE"
        assert refreshed.object_tracks[0].position_m == (2.0, 3.0, 0.0)
        assert refreshed.object_tracks[0].calibration_ids == ("survey-1",)
    finally:
        store.close()
