import pytest

from vigil.blueprint import CoordinateTransform, PoseState, register_blueprint
from vigil.gps import GPSFix, GPSObservationAdapter, GeodeticAnchor


def model():
    return register_blueprint(
        "site",
        "rev-1",
        frame_id="site/model",
        units="m",
        features=[{"feature_id": "anchor", "label": "Anchor", "position": [0, 0, 0]}],
    )


def adapter():
    anchor = GeodeticAnchor(0.0, 0.0, 0.0)
    transform = CoordinateTransform(
        source_frame="gps-enu",
        target_frame="site/model",
        provenance="surveyed-gps-anchor",
    )
    return GPSObservationAdapter(anchor, transform), anchor


def test_gps_adapter_converts_geodetic_fix_to_model_frame_and_preserves_accuracy():
    bridge, _ = adapter()
    fix = GPSFix(
        latitude_deg=0.0,
        longitude_deg=0.001,
        altitude_m=2.0,
        timestamp_ns=1234,
        horizontal_accuracy_m=4.0,
        vertical_accuracy_m=7.0,
        fix_id="fix-1",
    )
    observation = bridge.adapt(fix, model())
    assert observation.position_m[0] == pytest.approx(111.319, abs=0.2)
    assert observation.position_m[1] == pytest.approx(0.0, abs=0.2)
    assert observation.position_m[2] == pytest.approx(2.0, abs=0.2)
    assert observation.uncertainty_m == 7.0
    assert observation.frame_id == "site/model"
    assert observation.observation_id == "fix-1"
    assert "GPS WGS84" in observation.provenance


def test_gps_adapter_rejects_wrong_model_frame_and_invalid_fix():
    anchor = GeodeticAnchor(0.0, 0.0, 0.0)
    wrong_transform = CoordinateTransform(
        source_frame="gps-enu", target_frame="other/model"
    )
    bridge = GPSObservationAdapter(anchor, wrong_transform)
    with pytest.raises(ValueError, match="target frame"):
        bridge.adapt(GPSFix(0, 0, 0, 1, 2), model())
    with pytest.raises(ValueError, match="latitude"):
        GPSFix(91, 0, 0, 1, 2)
    with pytest.raises(ValueError, match="accuracy"):
        GPSFix(0, 0, 0, 1, 0)


def test_gps_anchor_requires_explicit_transform_from_enu_to_blueprint():
    anchor = GeodeticAnchor(41.0, -71.0, 10.0)
    with pytest.raises(ValueError, match="source frame"):
        GPSObservationAdapter(
            anchor,
            CoordinateTransform(source_frame="gps", target_frame="site/model"),
        )


def test_gps_accuracy_is_not_misrepresented_as_a_perfect_tracking_fix():
    from vigil.positioning import PoseEstimator

    bridge, _ = adapter()
    fix = GPSFix(0, 0, 0, 100, 12, fix_id="coarse-fix")
    observation = bridge.adapt(fix, model())
    # A single GPS source cannot independently establish TRACKING.
    pose = PoseEstimator().update(model(), (observation,), now_ns=100)
    assert pose.state == PoseState.DEGRADED
    assert pose.uncertainty_m is not None and pose.uncertainty_m >= 12
