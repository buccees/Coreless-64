import pytest

from vigil.blueprint import (
    CoordinateTransform,
    PoseEstimate,
    PoseState,
    nearest_feature,
    register_blueprint,
)


def sample_model(units="ft"):
    return register_blueprint(
        "facility-a",
        "rev-1",
        frame_id="facility-a/model",
        units=units,
        features=[
            {
                "feature_id": "door-1",
                "label": "North door",
                "position": [10, 0, 0],
                "feature_type": "door",
                "level": "L1",
                "zone": "north",
            },
            {
                "feature_id": "anchor-1",
                "label": "Survey anchor",
                "position": [0, 0, 0],
                "feature_type": "anchor",
            },
        ],
    )


def test_blueprint_registration_normalizes_feet_to_meters_and_hashes_revision():
    model = sample_model()
    assert model.features[0].position_m == pytest.approx((3.048, 0.0, 0.0))
    assert len(model.source_sha256) == 64
    assert model.source_sha256 == sample_model().source_sha256


def test_blueprint_rejects_unknown_units_and_duplicate_feature_ids():
    with pytest.raises(ValueError, match="unsupported blueprint units"):
        register_blueprint("x", "1", frame_id="x/model", units="parsecs", features=[
            {"feature_id": "a", "label": "A", "position": [0, 0, 0]}
        ])
    with pytest.raises(ValueError, match="unique"):
        register_blueprint("x", "1", frame_id="x/model", units="m", features=[
            {"feature_id": "a", "label": "A", "position": [0, 0, 0]},
            {"feature_id": "a", "label": "duplicate", "position": [1, 0, 0]},
        ])


def test_blueprint_rejects_non_finite_coordinates():
    with pytest.raises(ValueError, match="finite"):
        register_blueprint("x", "1", frame_id="x/model", units="m", features=[
            {"feature_id": "a", "label": "A", "position": [float("nan"), 0, 0]}
        ])


def test_coordinate_transform_applies_scale_rotation_and_translation():
    transform = CoordinateTransform(
        source_frame="device",
        target_frame="model",
        rotation=(0, -1, 0, 1, 0, 0, 0, 0, 1),
        translation=(10, 20, 3),
        scale=2,
        provenance="survey-control-points",
    )
    assert transform.apply((1, 2, 3), source_frame="device") == pytest.approx((6, 22, 9))
    with pytest.raises(ValueError, match="expects frame"):
        transform.apply((1, 2, 3), source_frame="gps")


def test_coordinate_transform_rejects_invalid_rotation_or_scale():
    with pytest.raises(ValueError, match="orthogonal"):
        CoordinateTransform(
            source_frame="a",
            target_frame="b",
            rotation=(1, 1, 0, 0, 1, 0, 0, 0, 1),
        )
    with pytest.raises(ValueError, match="positive"):
        CoordinateTransform(source_frame="a", target_frame="b", scale=0)


def test_nearest_feature_uses_model_coordinates_and_optional_radius():
    model = sample_model(units="m")
    result = nearest_feature(model, (0.5, 0, 0))
    assert result is not None
    feature, distance = result
    assert feature.feature_id == "anchor-1"
    assert distance == pytest.approx(0.5)
    assert nearest_feature(model, (0.5, 0, 0), max_distance_m=0.25) is None


def test_no_fix_is_distinct_from_valid_origin_pose():
    no_fix = PoseEstimate(
        model_id="facility-a",
        model_revision="rev-1",
        frame_id="facility-a/model",
        position_m=None,
        state=PoseState.LOST,
        uncertainty_m=None,
        observation_timestamp_ns=None,
        reason="no compatible observations",
    )
    origin_fix = PoseEstimate(
        model_id="facility-a",
        model_revision="rev-1",
        frame_id="facility-a/model",
        position_m=(0, 0, 0),
        state=PoseState.TRACKING,
        uncertainty_m=0.25,
        observation_timestamp_ns=123,
        provenance=("survey-anchor-1",),
    )
    assert no_fix.position_m is None
    assert origin_fix.position_m == (0, 0, 0)
    with pytest.raises(ValueError, match="requires position and uncertainty"):
        PoseEstimate(
            model_id="facility-a",
            model_revision="rev-1",
            frame_id="facility-a/model",
            position_m=None,
            state=PoseState.TRACKING,
            uncertainty_m=None,
            observation_timestamp_ns=123,
        )
