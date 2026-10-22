from vigil.blueprint import PoseEstimate, PoseState, register_blueprint
from vigil.csi_pipeline import CsiPipelineResult
from vigil.object_tracking import ObjectObservation, TrackingModality
from vigil.rf_csi import CsiFeatures, MotionState
from vigil.spatial_fusion_scene import assemble_fused_spatial_scene


def model_fixture():
    return register_blueprint(
        "arena", "rev-1", frame_id="arena/world", units="m",
        features=[
            {"feature_id": "entry", "label": "Entry", "position": [0, 0, 0], "level": "L1"},
            {"feature_id": "core", "label": "Core", "position": [10, 10, 0], "level": "L1"},
        ],
    )


def pose(model, timestamp=100):
    return PoseEstimate(
        model.model_id, model.revision, model.frame_id, (1, 2, 0),
        PoseState.TRACKING, 0.2, timestamp, provenance=("test-fixture",),
    )


def obs(model):
    return ObjectObservation(
        object_id="target", sensor_id="range-array", model_id=model.model_id,
        model_revision=model.revision, frame_id=model.frame_id, timestamp_ns=100,
        position_m=(3, 4, 0), uncertainty_m=0.2,
        modality=TrackingModality.RF_2_4_GHZ, provenance="calibrated-range",
    )


def csi(timestamp=100, active=True):
    return CsiPipelineResult(
        timestamp, "wifi-csi-1", 2437, CsiFeatures(32, .1, .2, .1, .6),
        MotionState(.6 if active else .05, active, 3 if active else 0, 0), 1,
    )


def test_fused_scene_exposes_sensor_status_and_keeps_spatial_quality_gate():
    model = model_fixture()
    result = assemble_fused_spatial_scene(
        model, pose(model), selected_level="L1", now_ns=100,
        observations=[obs(model)], csi_results=[csi()],
    )
    assert result.ready
    assert result.scene.object_count == 1
    assert result.evidence.active_csi_sensors == ("wifi-csi-1",)
    assert result.sensor_status[0].status == "MOTION EVIDENCE"
    assert result.sensor_status[2].status == "ACCEPTED"
    assert any("does not identify or locate" in note for note in result.warnings)


def test_fused_scene_warns_when_pose_is_stale_and_no_position_is_inferred():
    model = model_fixture()
    result = assemble_fused_spatial_scene(
        model, pose(model, timestamp=1), selected_level="L1", now_ns=100,
        csi_results=[csi(timestamp=1)], max_pose_age_ns=10, max_csi_skew_ns=10,
    )
    assert not result.ready
    assert result.scene.object_count == 0
    assert result.sensor_status[0].status == "STALE / REJECTED / NOT PROVIDED"
    assert any("pose_fresh" in warning for warning in result.warnings)
    assert any("No accepted spatial observations" in warning for warning in result.warnings)


def test_fused_scene_without_blueprint_fails_closed_and_reports_sensors():
    result = assemble_fused_spatial_scene(
        None, None, selected_level=None, now_ns=100, csi_results=[csi()],
    )
    assert not result.ready
    assert result.evidence.rejected_csi_count == 1
    assert any("No active blueprint" in warning for warning in result.warnings)
