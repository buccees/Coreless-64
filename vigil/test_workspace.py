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
