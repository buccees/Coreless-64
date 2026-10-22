import math

import pytest

from vigil.blueprint import register_blueprint
from vigil.csi_pipeline import CsiPipelineResult
from vigil.infrared_floor_mapping import InfraredFloorMap
from vigil.object_tracking import ObjectObservation, TrackingModality
from vigil.rf_csi import CsiFeatures, MotionState
from vigil.sensor_fusion import MultiSensorFusion


def model():
    return register_blueprint(
        "site", "r1", frame_id="building/world", units="m",
        features=[{"feature_id": "anchor", "label": "Anchor", "position": [0, 0, 0]}],
    )


def observation(active, *, timestamp=100, modality=TrackingModality.RF_2_4_GHZ):
    return ObjectObservation(
        object_id="cart", sensor_id="range-array", model_id=active.model_id,
        model_revision=active.revision, frame_id=active.frame_id,
        timestamp_ns=timestamp, position_m=(2.0, 3.0, 4.0),
        uncertainty_m=0.1, modality=modality, provenance="calibrated-position",
        association_id="cart-7",
    )


def csi(timestamp, *, active=True, sensor_id="wifi-1"):
    return CsiPipelineResult(
        timestamp_ns=timestamp, sensor_id=sensor_id, channel_mhz=2437,
        features=CsiFeatures(64, 0.1, 0.2, 0.3, 0.7),
        motion=MotionState(0.7 if active else 0.0, active, 3 if active else 0, 0),
        telemetry_row_id=1,
    )


def ir_map(active, *, timestamp=100, level="floor-1"):
    return InfraredFloorMap(
        sensor_id="thermal-1", model_id=active.model_id,
        model_revision=active.revision, frame_id=active.frame_id,
        level_id=level, timestamp_ns=timestamp, image_width=10, image_height=10,
        calibration_rms_m=0.1, samples=(),
    )


def test_fusion_keeps_csi_and_infrared_as_context_not_fake_positions():
    active = model()
    snapshot = MultiSensorFusion(active).fuse(
        now_ns=100, observations=[observation(active)],
        csi_results=[csi(100)], infrared_maps=[ir_map(active)],
    )
    assert len(snapshot.tracks) == 1
    assert snapshot.tracks[0].position_m == pytest.approx((2, 3, 4))
    assert snapshot.active_csi_sensors == ("wifi-1",)
    assert snapshot.infrared_levels == ("floor-1",)
    assert snapshot.accepted_observation_count == 1
    assert any("does not identify or locate" in note for note in snapshot.notes)


def test_fusion_rejects_stale_future_and_wrong_frame_evidence():
    active = model()
    wrong = ObjectObservation(
        object_id="bad", sensor_id="range", model_id=active.model_id,
        model_revision=active.revision, frame_id="wrong", timestamp_ns=100,
        position_m=(0, 0, 0), uncertainty_m=0.1,
        modality=TrackingModality.VISION, provenance="test",
    )
    snapshot = MultiSensorFusion(active, max_age_ns=10, max_csi_skew_ns=10, max_ir_age_ns=10).fuse(
        now_ns=100, observations=[wrong, observation(active, timestamp=1)],
        csi_results=[csi(50), csi(101, sensor_id="future")],
        infrared_maps=[ir_map(active, timestamp=1), ir_map(active, timestamp=101, level="future")],
    )
    assert snapshot.tracks == ()
    assert snapshot.accepted_observation_count == 0
    assert snapshot.rejected_observation_count == 2
    assert snapshot.rejected_csi_count == 2
    assert snapshot.rejected_infrared_count == 2


def test_fusion_validates_time_and_handles_empty_snapshot():
    active = model()
    fusion = MultiSensorFusion(active)
    with pytest.raises(ValueError, match="now_ns"):
        fusion.fuse(now_ns=-1)
    snapshot = fusion.fuse(now_ns=100)
    assert snapshot.tracks == ()
    assert any("no new object position" in note for note in snapshot.notes)
