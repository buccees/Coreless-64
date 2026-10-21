from vigil.blueprint import PoseEstimate, PoseState, register_blueprint
from vigil.object_tracking import ObjectTrack
from vigil.spatial_scene import assemble_spatial_scene
from vigil.terminal import VigilTerminal


def model_fixture():
    return register_blueprint(
        "arena", "rev-3", frame_id="arena/world", units="m",
        features=[
            {"feature_id": "entry", "label": "Entry", "position": [0, 0, 0], "level": "L1"},
            {"feature_id": "core", "label": "Core", "position": [10, 10, 3], "level": "L1"},
        ],
    )


def pose_fixture(model, *, timestamp=100, state=PoseState.TRACKING, revision=None, uncertainty=0.25):
    return PoseEstimate(
        model.model_id, revision or model.revision, model.frame_id,
        (2.0, 2.0, 0.0), state, uncertainty, timestamp,
        provenance=("uwb-anchor", "vision-map"),
    )


def track_fixture(model, *, conflict=False, timestamp=100, frame=None):
    return ObjectTrack(
        object_id="target-1", model_id=model.model_id, model_revision=model.revision,
        frame_id=frame or model.frame_id, position_m=(3, 3, 0),
        velocity_mps=(0.1, 0, 0), uncertainty_m=0.3, last_seen_ns=timestamp,
        sensor_ids=("uwb-1", "camera-1"), modalities=("uwb", "vision"),
        observation_count=2, association_id="entity-1", provenance=("calibrated",),
        conflict=conflict, conflict_reasons=("position_disagreement",) if conflict else (),
        conflicting_sensor_ids=("uwb-1", "camera-1") if conflict else (),
    )


def test_spatial_finisher_only_activates_when_deterministic_checks_pass():
    model = model_fixture()
    scene = assemble_spatial_scene(
        model, pose_fixture(model), (track_fixture(model),), selected_level="L1", now_ns=110,
    )
    assert scene.finishing_move_ready
    assert scene.banner == "FATALITY // SPATIAL SCENE LOCKED"
    assert scene.view is not None
    assert scene.object_count == 1
    assert scene.conflict_count == 0
    assert all(check.passed for check in scene.checks if check.name != "infrared_overlay_optional")


def test_finisher_denied_for_stale_pose_wrong_frame_or_conflicting_tracks():
    model = model_fixture()
    stale = assemble_spatial_scene(
        model, pose_fixture(model, timestamp=1), selected_level="L1", now_ns=1000,
        max_pose_age_ns=10,
    )
    assert not stale.finishing_move_ready
    assert "pose_fresh" in {check.name for check in stale.checks if not check.passed}

    wrong_revision = assemble_spatial_scene(
        model, pose_fixture(model, revision="old"), selected_level="L1", now_ns=110,
    )
    assert not wrong_revision.finishing_move_ready
    assert wrong_revision.banner.startswith("FATALITY DENIED")

    conflict = assemble_spatial_scene(
        model, pose_fixture(model), (track_fixture(model, conflict=True),),
        selected_level="L1", now_ns=110,
    )
    assert not conflict.finishing_move_ready
    assert conflict.conflict_count == 1


def test_finisher_ignores_stale_and_wrong_frame_object_tracks():
    model = model_fixture()
    scene = assemble_spatial_scene(
        model, pose_fixture(model),
        (track_fixture(model, timestamp=1), track_fixture(model, frame="device/local")),
        selected_level="L1", now_ns=1000, max_object_age_ns=10,
    )
    assert scene.finishing_move_ready
    assert scene.object_count == 0


def test_terminal_shows_earned_or_denied_finisher_and_reason_codes():
    model = model_fixture()
    scene = assemble_spatial_scene(
        model, pose_fixture(model, timestamp=1), selected_level="L1", now_ns=100,
        max_pose_age_ns=10,
    )
    output = VigilTerminal(color=False).render(
        model, pose_fixture(model, timestamp=1), now_ns=100, selected_level="L1",
        spatial_scene=scene,
    )
    assert "FATALITY DENIED // VALIDATION INCOMPLETE" in output
    assert "FAIL pose_fresh" in output


def test_finisher_requires_a_real_selected_floor_when_model_has_floor_labels():
    model = model_fixture()
    scene = assemble_spatial_scene(
        model, pose_fixture(model), selected_level=None, now_ns=110,
    )
    assert not scene.finishing_move_ready
    assert "active_floor_selected" in {
        check.name for check in scene.checks if not check.passed
    }
