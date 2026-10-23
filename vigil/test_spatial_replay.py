"""Deterministic end-to-end replay across VIGIL workspace and operator outputs."""
from __future__ import annotations

from vigil.blueprint import register_blueprint
from vigil.object_tracking import ObjectObservation, TrackingModality
from vigil.positioning import SpatialObservation
from vigil.spatial_regions import SpatialRegion
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


def _object(model, timestamp_ns, x, *, sensor_id="uwb-array", modality=TrackingModality.UWB):
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
        independence_group="uwb-array",
        calibration_status="verified",
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
    assert second_api["regions"][0]["inside"] is False


def test_replay_is_repeatable_without_wall_clock_or_synthetic_fallbacks():
    first = _run_replay()
    second = _run_replay()
    assert first[3] == second[3]
    assert first[7] == second[7]
