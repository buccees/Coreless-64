"""Deterministic end-to-end replay across VIGIL workspace and operator outputs."""
from __future__ import annotations

from vigil.blueprint import register_blueprint
from vigil.object_tracking import ObjectObservation, TrackingModality
from vigil.positioning import SpatialObservation
from vigil.spatial_regions import SpatialRegion
from vigil.spatial_registry_store import SpatialRegistryStore
from vigil.spatial_snapshot import build_spatial_snapshot
from vigil.workspace import SensorBatch, SpatialWorkspace


class ReplayProvider:
    """Finite deterministic sensor replay; no wall clock or hardware required."""

    def __init__(self, batches):
        self._batches = iter(batches)

    def read(self):
        return next(self._batches)


def _position(model, source, timestamp_ns, x):
    return SpatialObservation(
        observation_id=f"{source}-{timestamp_ns}",
        source_id=source,
        model_id=model.model_id,
        model_revision=model.revision,
        frame_id=model.frame_id,
        timestamp_ns=timestamp_ns,
        position_m=(x, 0.0, 0.0),
        uncertainty_m=0.2,
        provenance="deterministic-replay",
    )


def _object(model, timestamp_ns, x, *, sensor_id="uwb-array", modality=TrackingModality.UWB,
            calibration_status="verified", independence_group="uwb-array"):
    return ObjectObservation(
        object_id="cart-7",
        sensor_id=sensor_id,
        model_id=model.model_id,
        model_revision=model.revision,
        frame_id=model.frame_id,
        timestamp_ns=timestamp_ns,
        position_m=(x, 2.0, 0.0),
        uncertainty_m=0.15,
        modality=modality,
        provenance="deterministic-replay-ranging" if modality is TrackingModality.UWB else "deterministic-replay-vision",
        association_id="cart-7-entity",
        independence_group=independence_group,
        calibration_status=calibration_status,
        calibration_ids=("survey-replay-v1",),
        lineage_declared=True,
    )


def _run_replay():
    workspace = SpatialWorkspace()
    model = workspace.import_blueprint(
        '{"schema_version":1,"model_id":"replay-site","revision":"r1",'
        '"frame_id":"replay-site/world","units":"m","features":['
        '{"feature_id":"origin","label":"Origin","position":[0,0,0],"level":"L1"}]}',
        activate=True,
    )
    workspace.select_level("L1")
    workspace.register_region(SpatialRegion(
        "west-zone", "West zone", model.model_id, model.revision, model.frame_id,
        ((-1, -1), (1.5, -1), (1.5, 1), (-1, 1)),
        min_z_m=-1, max_z_m=1, level="L1", zone="west",
    ))
    workspace.register_sensor_provider("replay", ReplayProvider((
        SensorBatch(
            position_observations=(
                _position(model, "uwb-pose", 100, 0.5),
                _position(model, "vision-pose", 100, 0.5),
            ),
            object_observations=(_object(model, 100, 1.0), _object(model, 100, 1.0, sensor_id="camera-cart", modality=TrackingModality.VISION)),
        ),
        SensorBatch(
            position_observations=(
                _position(model, "uwb-pose", 200, 2.0),
                _position(model, "vision-pose", 200, 2.0),
            ),
            object_observations=(_object(model, 200, 2.0), _object(model, 200, 2.0, sensor_id="camera-cart", modality=TrackingModality.VISION)),
        ),
    )))

    first_poll = workspace.poll_sensors()
    first = workspace.refresh(now_ns=100)
    first_scene = workspace.spatial_scene(now_ns=100)
    first_snapshot = build_spatial_snapshot(workspace, now_ns=100)

    second_poll = workspace.poll_sensors()
    second = workspace.refresh(now_ns=200)
    second_scene = workspace.spatial_scene(now_ns=200)
    second_snapshot = build_spatial_snapshot(workspace, now_ns=200)
    return (first_poll, first, first_scene, first_snapshot,
            second_poll, second, second_scene, second_snapshot)


def test_deterministic_replay_connects_pose_tracks_regions_scene_and_operator_snapshot():
    (first_poll, first, first_scene, first_api,
     second_poll, second, second_scene, second_api) = _run_replay()

    assert [(item.provider_id, item.state, item.accepted) for item in first_poll] == [
        ("replay", "ONLINE", 4)
    ]
    assert first.pose is not None and first.pose.position_m == (0.5, 0.0, 0.0)
    assert first.region_results[0].inside is True
    assert first_scene.finishing_move_ready
    assert first_api["pose"]["presence_state"] == "CURRENT"
    assert first_api["regions"][0]["inside"] is True

    assert [(item.provider_id, item.state, item.accepted) for item in second_poll] == [
        ("replay", "ONLINE", 4)
    ]
    assert second.pose is not None and second.pose.position_m == (2.0, 0.0, 0.0)
    assert second.region_results[0].inside is False
    assert second_scene.finishing_move_ready
    assert len(second.object_tracks) == 1
    track = second.object_tracks[0]
    assert track.object_id == "cart-7"
    assert track.position_m == (2.0, 2.0, 0.0)
    assert track.observation_count == 4
    assert track.sensor_ids == ("camera-cart", "uwb-array")
    assert track.calibration_status == "verified"
    assert track.calibration_ids == ("survey-replay-v1",)
    assert len(track.position_history_m) >= 2

    api_object = second_api["objects"][0]
    assert api_object["position_m"] == [2.0, 2.0, 0.0]
    assert api_object["presence_state"] == "CURRENT"
    assert api_object["observation_count"] == 4
    assert api_object["calibration_ids"] == ["survey-replay-v1"]
    assert len(api_object["motion_trail_m"]) >= 2
    assert api_object["motion_trail_m"][-1]["sensor_ids"] == ["camera-cart", "uwb-array"]
    assert len(api_object["sensor_observations"]) == 4
    assert {item["sensor_id"] for item in api_object["sensor_observations"]} == {"camera-cart", "uwb-array"}
    assert all(item["quality_status"] == "FRESH" for item in api_object["sensor_observations"])
    assert all(item["fusion_disposition"] == "HISTORICAL_ONLY" for item in api_object["sensor_observations"] if item["timestamp_ns"] == "100")
    assert all(item["fusion_disposition"] == "CONTRIBUTED_TO_FUSION" for item in api_object["sensor_observations"] if item["timestamp_ns"] == "200")
    latest_measurements = [item for item in api_object["sensor_observations"] if item["timestamp_ns"] == "200"]
    assert len(latest_measurements) == 2
    assert {item["modality"] for item in latest_measurements} == {"vision", "uwb"}
    assert all(item["position_m"] == [2.0, 2.0, 0.0] for item in latest_measurements)
    assert second_api["regions"][0]["inside"] is False


def test_replay_is_repeatable_without_wall_clock_or_synthetic_fallbacks():
    first = _run_replay()
    second = _run_replay()
    assert first[3] == second[3]
    assert first[7] == second[7]


def test_snapshot_degrades_track_validity_without_erasing_last_known_position():
    workspace = SpatialWorkspace()
    model = workspace.import_blueprint(
        '{"schema_version":1,"model_id":"validity-site","revision":"r1",'
        '"frame_id":"validity-site/world","units":"m","features":[]}',
        activate=True,
    )
    workspace.ingest_object_observations((_object(model, 100, 3.0),))
    workspace.refresh(now_ns=100)
    current = build_spatial_snapshot(workspace, now_ns=100)
    assert current["objects"][0]["track_validity"] == "CURRENT"
    assert current["objects"][0]["position_m"] == [3.0, 2.0, 0.0]

    stale = build_spatial_snapshot(workspace, now_ns=2_000_000_000, max_age_ns=1_000)
    assert stale["objects"][0]["track_validity"] == "STALE_LAST_KNOWN"
    assert "measurement_age_exceeds_max_age" in stale["objects"][0]["track_validity_reasons"]
    assert stale["objects"][0]["position_m"] == [3.0, 2.0, 0.0]
    assert len(stale["objects"][0]["sensor_observations"]) == 1



def test_failed_calibration_degrades_track_and_remains_visible_in_sensor_evidence():
    workspace = SpatialWorkspace()
    model = workspace.import_blueprint(
        '{"schema_version":1,"model_id":"calibration-site","revision":"r1",'
        '"frame_id":"calibration-site/world","units":"m","features":[]}',
        activate=True,
    )
    workspace.ingest_object_observations((
        _object(model, 100, 3.0, calibration_status="failed"),
    ))
    workspace.refresh(now_ns=100)
    snapshot = build_spatial_snapshot(workspace, now_ns=100)
    item = snapshot["objects"][0]

    assert item["track_validity"] == "DEGRADED"
    assert "calibration_failed" in item["track_validity_reasons"]
    assert item["position_m"] == [3.0, 2.0, 0.0]
    assert item["sensor_observations"][0]["quality_status"] == "UNCALIBRATED"
    assert "uncalibrated" in item["sensor_observations"][0]["quality_flags"]


def test_conflicting_independent_sensor_positions_degrade_track_without_midpoint():
    workspace = SpatialWorkspace()
    model = workspace.import_blueprint(
        '{"schema_version":1,"model_id":"conflict-site","revision":"r1",'
        '"frame_id":"conflict-site/world","units":"m","features":[]}',
        activate=True,
    )
    workspace.ingest_object_observations((
        _object(model, 100, 0.0, sensor_id="uwb-left", independence_group="uwb-left"),
        _object(model, 100, 10.0, sensor_id="camera-right",
                modality=TrackingModality.VISION, independence_group="camera-right"),
    ))
    workspace.refresh(now_ns=100)
    snapshot = build_spatial_snapshot(workspace, now_ns=100)
    item = snapshot["objects"][0]

    assert item["track_validity"] == "DEGRADED"
    assert "sensor_conflict_unresolved" in item["track_validity_reasons"]
    assert item["conflict"] is True
    assert item["position_m"] in ([0.0, 2.0, 0.0], [10.0, 2.0, 0.0])
    assert item["position_m"] not in ([5.0, 2.0, 0.0],)
    assert set(item["conflicting_sensor_ids"]) == {"uwb-left", "camera-right"}


def test_expected_sensor_coverage_distinguishes_unpolled_no_report_and_in_scope_report():
    workspace = SpatialWorkspace()
    model = workspace.import_blueprint(
        '{"schema_version":1,"model_id":"coverage-site","revision":"r1",'
        '"frame_id":"coverage-site/world","units":"m","features":[]}', activate=True)
    workspace.register_region(SpatialRegion(
        "checkout", "Checkout", model.model_id, model.revision, model.frame_id,
        ((0, 0), (5, 0), (5, 5), (0, 5)), min_z_m=-1, max_z_m=2))
    workspace.register_expected_sensor("cart-camera", provider_id="camera-provider", region_ids=("checkout",), max_age_ns=500)
    assert build_spatial_snapshot(workspace, now_ns=100)["expected_sensor_coverage"][0]["state"] == "UNPOLLED"
    workspace.register_sensor_provider("camera-provider", ReplayProvider((SensorBatch(),)))
    workspace.poll_sensors()
    assert build_spatial_snapshot(workspace, now_ns=100)["expected_sensor_coverage"][0]["state"] == "NO_REPORT_IN_SCOPE"
    workspace.ingest_object_observations((_object(model, 200, 2.0, sensor_id="cart-camera", modality=TrackingModality.VISION, independence_group="cart-camera"),))
    result = build_spatial_snapshot(workspace, now_ns=250)["expected_sensor_coverage"][0]
    assert result["state"] == "REPORTING_IN_SCOPE" and result["age_ns"] == "50"


def test_expected_sensor_coverage_ignores_observations_outside_declared_region():
    workspace = SpatialWorkspace()
    model = workspace.import_blueprint(
        '{"schema_version":1,"model_id":"coverage-outside","revision":"r1",'
        '"frame_id":"coverage-outside/world","units":"m","features":[]}', activate=True)
    workspace.register_region(SpatialRegion(
        "west", "West", model.model_id, model.revision, model.frame_id,
        ((0, 0), (5, 0), (5, 5), (0, 5)), min_z_m=-1, max_z_m=2))
    workspace.register_expected_sensor("cart-camera", provider_id="camera-provider", region_ids=("west",))
    workspace.register_sensor_provider("camera-provider", ReplayProvider((SensorBatch(object_observations=(
        _object(model, 200, 9.0, sensor_id="cart-camera", modality=TrackingModality.VISION, independence_group="cart-camera"),)),)))
    workspace.poll_sensors()
    result = build_spatial_snapshot(workspace, now_ns=250)["expected_sensor_coverage"][0]
    assert result["state"] == "NO_REPORT_IN_SCOPE" and result["latest_observation_ns"] is None


def test_expected_sensor_configuration_survives_workspace_restart():
    store = SpatialRegistryStore()
    try:
        workspace = SpatialWorkspace(registry_store=store)
        model = workspace.import_blueprint(
            '{"schema_version":1,"model_id":"persistent-coverage","revision":"r1",'
            '"frame_id":"persistent-coverage/world","units":"m","features":[]}', activate=True)
        workspace.register_region(SpatialRegion(
            "checkout", "Checkout", model.model_id, model.revision, model.frame_id,
            ((0, 0), (5, 0), (5, 5), (0, 5)), min_z_m=-1, max_z_m=2))
        workspace.register_expected_sensor("cart-camera", provider_id="camera-provider",
            region_ids=("checkout",), max_age_ns=750)
        restarted = SpatialWorkspace(registry_store=store)
        assert restarted.expected_sensor_coverage == (
            type(workspace.expected_sensor_coverage[0])(
                "cart-camera", "camera-provider", ("checkout",), 750),
        )
        assert build_spatial_snapshot(restarted, now_ns=100)["expected_sensor_coverage"][0]["state"] == "UNPOLLED"
        assert restarted.unregister_expected_sensor("cart-camera") is True
        assert SpatialWorkspace(registry_store=store).expected_sensor_coverage == ()
    finally:
        store.close()


def test_provider_lifecycle_retains_last_success_and_counts_failures_then_recovers():
    class FlakyProvider:
        def __init__(self):
            self.fail = False
        def read(self):
            if self.fail:
                raise OSError("device temporarily unavailable")
            return SensorBatch()

    workspace = SpatialWorkspace()
    provider = FlakyProvider()
    workspace.register_sensor_provider("flaky", provider)
    online = workspace.poll_sensors()[0]
    assert online.state == "ONLINE" and online.last_success_ns is not None
    provider.fail = True
    failed = workspace.poll_sensors()[0]
    assert failed.state == "ERROR"
    assert failed.consecutive_failures == 1
    assert failed.last_success_ns == online.last_success_ns
    failed_again = workspace.poll_sensors()[0]
    assert failed_again.consecutive_failures == 2
    provider.fail = False
    recovered = workspace.poll_sensors()[0]
    assert recovered.state == "ONLINE"
    assert recovered.consecutive_failures == 0
    assert recovered.last_success_ns is not None
    assert workspace.unregister_sensor_provider("flaky") is True
    disconnected = next(s for s in workspace.sensor_poll_statuses if s.provider_id == "flaky")
    assert disconnected.state == "DISCONNECTED"
    assert disconnected.last_success_ns == recovered.last_success_ns


def test_expected_sensor_coverage_distinguishes_stale_report_from_no_report():
    workspace = SpatialWorkspace()
    model = workspace.import_blueprint(
        '{"schema_version":1,"model_id":"stale-coverage","revision":"r1",'
        '"frame_id":"stale-coverage/world","units":"m","features":[]}', activate=True)
    workspace.register_region(SpatialRegion(
        "checkout", "Checkout", model.model_id, model.revision, model.frame_id,
        ((0, 0), (5, 0), (5, 5), (0, 5)), min_z_m=-1, max_z_m=2))
    workspace.register_expected_sensor("cam-1", provider_id="camera-provider",
                                       region_ids=("checkout",), max_age_ns=50)
    workspace.register_sensor_provider("camera-provider", ReplayProvider((SensorBatch(object_observations=(
        _object(model, 100, 3.0, sensor_id="cam-1", modality=TrackingModality.VISION,
                independence_group="cam-1"),
    )),)))
    workspace.poll_sensors()
    stale = build_spatial_snapshot(workspace, now_ns=200)["expected_sensor_coverage"][0]
    assert stale["state"] == "STALE_REPORT"
    assert stale["latest_observation_ns"] == "100"
    assert stale["age_ns"] == "100"
    assert stale["max_age_ns"] == "50"
