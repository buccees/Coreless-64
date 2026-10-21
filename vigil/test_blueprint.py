import pytest

from vigil.blueprint import (
    CoordinateTransform,
    PoseEstimate,
    PoseState,
    load_blueprint_json,
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
    with pytest.raises(ValueError, match="unit length"):
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



def test_json_manifest_ingestion_preserves_floor_zone_and_normalizes_units():
    import json

    document = json.dumps({
        "schema_version": 1,
        "model_id": "site-7",
        "revision": "floor-plan-r2",
        "frame_id": "site-7/model",
        "units": "cm",
        "features": [
            {
                "feature_id": "lift-a",
                "label": "Elevator A",
                "position": [125, 250, 0],
                "feature_type": "elevator",
                "level": "B1",
                "zone": "east",
            }
        ],
        "metadata": {"source_name": "survey export"},
    })
    model = load_blueprint_json(document)
    assert model.features[0].position_m == pytest.approx((1.25, 2.5, 0.0))
    assert model.features[0].level == "B1"
    assert model.features[0].zone == "east"
    assert model.metadata["source_name"] == "survey export"


def test_json_manifest_rejects_unknown_schema_bad_json_nonfinite_and_oversize():
    import json

    valid = {
        "schema_version": 1,
        "model_id": "m",
        "revision": "1",
        "frame_id": "m/model",
        "units": "m",
        "features": [{"feature_id": "a", "label": "A", "position": [0, 0, 0]}],
    }
    with pytest.raises(ValueError, match="schema_version"):
        load_blueprint_json(json.dumps({**valid, "schema_version": 2}))
    with pytest.raises(ValueError, match="invalid blueprint JSON"):
        load_blueprint_json("{not-json")
    with pytest.raises(ValueError, match="non-finite"):
        load_blueprint_json(json.dumps(valid).replace("[0, 0, 0]", "[NaN, 0, 0]"))
    with pytest.raises(ValueError, match="byte limit"):
        load_blueprint_json(json.dumps(valid), max_bytes=10)


def test_json_manifest_requires_object_and_utf8_bytes():
    with pytest.raises(ValueError, match="JSON object"):
        load_blueprint_json("[]")
    with pytest.raises(ValueError, match="UTF-8"):
        load_blueprint_json(b"\xff\xfe")
