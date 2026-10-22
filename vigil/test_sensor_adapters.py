import math

import pytest

from vigil.blueprint import register_blueprint
from vigil.object_tracking import TrackingModality
from vigil.sensor_adapters import (
    RangeMeasurement,
    acoustic_tof_range_m,
    rf_tof_range_m,
    to_object_observation,
    trilaterate_3d,
)


def model():
    return register_blueprint(
        "site", "r1", frame_id="building/world", units="m",
        features=[{"feature_id": "anchor", "label": "Anchor", "position": [0, 0, 0]}],
    )


def ranges(m, target=(2.0, 3.0, 4.0), *, modality=TrackingModality.RF_2_4_GHZ):
    anchors = ((0, 0, 0), (10, 0, 0), (0, 10, 0), (0, 0, 10))
    return [
        RangeMeasurement(
            sensor_id=f"anchor-{i}", object_id="cart", model_id=m.model_id,
            model_revision=m.revision, frame_id=m.frame_id, timestamp_ns=100,
            anchor_position_m=anchor,
            range_m=math.dist(anchor, target), uncertainty_m=0.05,
            modality=modality, provenance="calibrated-tof",
        )
        for i, anchor in enumerate(anchors)
    ]


def test_rf_and_acoustic_tof_use_distinct_propagation_speeds():
    assert rf_tof_range_m(2e-9) == pytest.approx(0.299792458)
    assert acoustic_tof_range_m(0.01) == pytest.approx(1.715)
    with pytest.raises(ValueError):
        rf_tof_range_m(0)
    with pytest.raises(ValueError):
        acoustic_tof_range_m(0.01, sound_speed_mps=0)


def test_3d_trilateration_and_object_tracker_adapter():
    active = model()
    measurements = ranges(active)
    position, residual = trilaterate_3d(measurements)
    assert position == pytest.approx((2.0, 3.0, 4.0))
    assert residual == pytest.approx(0.0, abs=1e-8)
    observation = to_object_observation(active, measurements)
    assert observation.position_m == pytest.approx((2.0, 3.0, 4.0))
    assert observation.modality == TrackingModality.RF_2_4_GHZ
    assert "trilateration" in observation.provenance


def test_trilateration_rejects_too_few_mismatched_or_degenerate_ranges():
    active = model()
    measurements = ranges(active)
    with pytest.raises(ValueError, match="at least four"):
        trilaterate_3d(measurements[:3])
    wrong_frame = list(measurements)
    wrong_frame[1] = RangeMeasurement(
        sensor_id="bad", object_id="cart", model_id=active.model_id,
        model_revision=active.revision, frame_id="wrong/frame", timestamp_ns=100,
        anchor_position_m=(10, 0, 0), range_m=math.sqrt(89),
        uncertainty_m=0.1, modality=TrackingModality.RF_2_4_GHZ, provenance="test",
    )
    with pytest.raises(ValueError, match="share object, model revision, and coordinate frame"):
        trilaterate_3d(wrong_frame)
    same_plane = [
        RangeMeasurement(
            sensor_id=f"flat-{i}", object_id="cart", model_id=active.model_id,
            model_revision=active.revision, frame_id=active.frame_id, timestamp_ns=100,
            anchor_position_m=anchor, range_m=math.dist(anchor, (2, 3, 4)),
            uncertainty_m=0.1, modality=TrackingModality.RF_2_4_GHZ, provenance="test",
        )
        for i, anchor in enumerate(((0, 0, 0), (10, 0, 0), (0, 10, 0), (10, 10, 0)))
    ]
    with pytest.raises(ValueError, match="degenerate"):
        trilaterate_3d(same_plane)


def test_failed_calibration_is_rejected_before_positioning():
    active = model()
    measurements = ranges(active)
    first = measurements[0]
    measurements[0] = RangeMeasurement(
        sensor_id=first.sensor_id, object_id=first.object_id, model_id=first.model_id,
        model_revision=first.model_revision, frame_id=first.frame_id,
        timestamp_ns=first.timestamp_ns, anchor_position_m=first.anchor_position_m,
        range_m=first.range_m, uncertainty_m=first.uncertainty_m,
        modality=first.modality, provenance=first.provenance,
        calibration_status="failed", calibration_id="cal-2026-04",
    )
    with pytest.raises(ValueError, match="failed calibration"):
        trilaterate_3d(measurements)


def test_adapter_propagates_declared_shared_lineage_and_marks_unverified_calibration():
    active = model()
    measurements = ranges(active)
    measurements = [
        RangeMeasurement(
            sensor_id=item.sensor_id, object_id=item.object_id, model_id=item.model_id,
            model_revision=item.model_revision, frame_id=item.frame_id,
            timestamp_ns=item.timestamp_ns, anchor_position_m=item.anchor_position_m,
            range_m=item.range_m, uncertainty_m=item.uncertainty_m,
            modality=item.modality, provenance=item.provenance,
            independence_group="shared-ranging-chain",
            calibration_status="unverified", calibration_id="cal-check-pending",
        )
        for item in measurements
    ]
    observation = to_object_observation(active, measurements)
    assert observation.independence_group == "shared-ranging-chain"
    assert "calibration=UNVERIFIED" in observation.provenance
    assert "cal-check-pending" in observation.provenance


def test_adapter_does_not_invent_one_lineage_for_mixed_or_missing_groups():
    active = model()
    measurements = ranges(active)
    measurements[0] = RangeMeasurement(
        sensor_id=measurements[0].sensor_id, object_id=measurements[0].object_id,
        model_id=measurements[0].model_id, model_revision=measurements[0].model_revision,
        frame_id=measurements[0].frame_id, timestamp_ns=measurements[0].timestamp_ns,
        anchor_position_m=measurements[0].anchor_position_m, range_m=measurements[0].range_m,
        uncertainty_m=measurements[0].uncertainty_m, modality=measurements[0].modality,
        provenance=measurements[0].provenance, independence_group="one-source",
    )
    observation = to_object_observation(active, measurements)
    assert observation.independence_group is None


def test_single_solve_cannot_mix_rf_and_acoustic_measurements():
    active = model()
    measurements = ranges(active)
    last = measurements[-1]
    measurements[-1] = RangeMeasurement(
        sensor_id=last.sensor_id, object_id=last.object_id, model_id=last.model_id,
        model_revision=last.model_revision, frame_id=last.frame_id,
        timestamp_ns=last.timestamp_ns, anchor_position_m=last.anchor_position_m,
        range_m=last.range_m, uncertainty_m=last.uncertainty_m,
        modality=TrackingModality.ACOUSTIC_SONAR, provenance=last.provenance,
    )
    with pytest.raises(ValueError, match="single sensing modality"):
        to_object_observation(active, measurements)
