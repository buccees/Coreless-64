import pytest
from vigil.blueprint import PoseEstimate, PoseState, register_blueprint
from vigil.object_tracking import ObjectTrack
from vigil.infrared_floor_mapping import InfraredFloorMap
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
    assert scene.stale_track_count == 1
    assert scene.view is not None
    assert [(item.object_id, item.presence_state) for item in scene.view.objects] == [
        ("target-1", "STALE")
    ]


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



def ir_map(model, *, timestamp=100, revision=None, frame=None, level="L1"):
    return InfraredFloorMap(
        sensor_id="thermal-1", model_id=model.model_id,
        model_revision=revision or model.revision,
        frame_id=frame or model.frame_id, level_id=level,
        timestamp_ns=timestamp, image_width=64, image_height=64,
        calibration_rms_m=0.05, samples=(),
    )


def test_spatial_scene_only_exposes_fresh_aligned_ir_floor_maps():
    model = model_fixture()
    scene = assemble_spatial_scene(
        model, pose_fixture(model),
        infrared_maps=(
            ir_map(model, timestamp=95, level="L1"),
            ir_map(model, timestamp=70, level="L2"),
            ir_map(model, timestamp=120, level="L3"),
            ir_map(model, revision="old", level="L4"),
        ),
        selected_level="L1", now_ns=100, max_ir_age_ns=10,
    )
    assert scene.infrared_levels == ("L1",)
    ir_check = next(check for check in scene.checks if check.name == "infrared_overlay_optional")
    assert ir_check.passed
    assert "1 fresh aligned map(s)" in ir_check.detail
    assert "1 stale" in ir_check.detail
    assert "1 future-dated" in ir_check.detail
    assert "1 frame/revision/floor-invalid" in ir_check.detail
    assert scene.finishing_move_ready


def test_stale_ir_overlay_does_not_appear_in_scene_floor_list():
    model = model_fixture()
    scene = assemble_spatial_scene(
        model, pose_fixture(model), infrared_maps=(ir_map(model, timestamp=1),),
        selected_level="L1", now_ns=100, max_ir_age_ns=10,
    )
    assert scene.infrared_levels == ()
    assert scene.finishing_move_ready



def test_scene_reports_usable_uncertain_and_conflicted_tracks_separately():
    model = model_fixture()
    usable = track_fixture(model)
    uncertain = ObjectTrack(
        **{**usable.__dict__, "object_id": "target-uncertain",
           "uncertainty_m": 2.5, "conflict": False, "conflict_reasons": (),
           "conflicting_sensor_ids": ()}
    )
    conflicted = ObjectTrack(
        **{**usable.__dict__, "object_id": "target-conflicted",
           "conflict": True, "conflict_reasons": ("position_disagreement",),
           "conflicting_sensor_ids": ("camera-1", "uwb-1")}
    )
    scene = assemble_spatial_scene(
        model, pose_fixture(model), (usable, uncertain, conflicted),
        selected_level="L1", now_ns=110, max_track_uncertainty_m=1.0,
    )
    assert scene.usable_track_count == 1
    assert scene.uncertain_track_count == 1
    assert scene.conflict_count == 1
    assert scene.unknown_uncertainty_track_count == 0
    quality = next(check for check in scene.checks if check.name == "object_track_quality")
    assert quality.passed
    assert "1 usable track(s)" in quality.detail
    assert "1 uncertain track(s)" in quality.detail
    assert "1 conflicted track(s)" in quality.detail
    assert not scene.finishing_move_ready


def test_scene_unknown_track_uncertainty_fails_quality_gate():
    model = model_fixture()
    track = track_fixture(model)
    unknown = ObjectTrack(
        **{**track.__dict__, "object_id": "target-unknown", "uncertainty_m": float("nan")}
    )
    scene = assemble_spatial_scene(
        model, pose_fixture(model), (unknown,), selected_level="L1", now_ns=110,
    )
    assert scene.unknown_uncertainty_track_count == 1
    assert not scene.finishing_move_ready
    assert "object_track_uncertainty_known" in {
        check.name for check in scene.checks if not check.passed
    }


def test_scene_rejects_invalid_track_uncertainty_threshold():
    model = model_fixture()
    with pytest.raises(ValueError, match="max_track_uncertainty_m"):
        assemble_spatial_scene(
            model, pose_fixture(model), selected_level="L1", now_ns=110,
            max_track_uncertainty_m=float("inf"),
        )



def test_scene_blocks_failed_calibration_and_surfaces_unverified_lineage():
    model = model_fixture()
    base = track_fixture(model)
    failed = ObjectTrack(
        **{**base.__dict__, "object_id": "failed-calibration",
           "calibration_status": "failed", "calibration_ids": ("cal-17",),
           "lineage_declared": True}
    )
    scene = assemble_spatial_scene(
        model, pose_fixture(model), (failed,), selected_level="L1", now_ns=110,
    )
    assert not scene.finishing_move_ready
    calibration_gate = next(check for check in scene.checks if check.name == "track_calibration_valid")
    assert not calibration_gate.passed
    assert "failed calibration" in calibration_gate.detail

    unverified = ObjectTrack(
        **{**base.__dict__, "object_id": "unverified-calibration",
           "calibration_status": "unverified", "lineage_declared": False}
    )
    warning_scene = assemble_spatial_scene(
        model, pose_fixture(model), (unverified,), selected_level="L1", now_ns=110,
    )
    assert warning_scene.finishing_move_ready
    calibration_warning = next(check for check in warning_scene.checks if check.name == "track_calibration_verified")
    lineage_warning = next(check for check in warning_scene.checks if check.name == "source_lineage_declared")
    assert calibration_warning.passed and "WARNING" in calibration_warning.detail
    assert lineage_warning.passed and "WARNING" in lineage_warning.detail
