import pytest

from vigil.blueprint import PoseEstimate, PoseState, register_blueprint
from vigil.spatial_query import SpatialQueryEngine, SpatialQueryStatus


def model():
    return register_blueprint(
        "site", "rev-1", frame_id="site/world", units="m",
        features=[
            {"feature_id": "entry", "label": "Entry", "position": [0, 0, 0], "level": "L1", "zone": "public"},
            {"feature_id": "lab", "label": "Lab", "position": [5, 0, 0], "level": "L1", "zone": "restricted"},
            {"feature_id": "upper", "label": "Upper room", "position": [5, 0, 4], "level": "L2", "zone": "research"},
        ],
    )


def pose(active, *, position=(1, 0, 0), timestamp=100, state=PoseState.TRACKING, uncertainty=0.2, revision=None, frame=None):
    return PoseEstimate(
        active.model_id, revision or active.revision, frame or active.frame_id,
        position, state, uncertainty, timestamp, provenance=("test-sensor",),
    )


def test_query_returns_nearest_feature_zone_and_nearby_features():
    active = model()
    result = SpatialQueryEngine(active).evaluate(
        pose(active), now_ns=110, nearby_radius_m=1.1,
    )
    assert result.status == SpatialQueryStatus.OK
    assert result.nearest_feature_id == "entry"
    assert result.nearest_feature_label == "Entry"
    assert result.nearest_feature_distance_m == pytest.approx(1.0)
    assert result.level == "L1"
    assert result.zone == "public"
    assert result.nearby_feature_ids == ("entry",)
    assert result.position_m == (1.0, 0.0, 0.0)


@pytest.mark.parametrize("kwargs,expected", [
    ({"timestamp": 1}, SpatialQueryStatus.STALE),
    ({"timestamp": 111}, SpatialQueryStatus.FUTURE_TIMESTAMP),
    ({"revision": "old"}, SpatialQueryStatus.MODEL_MISMATCH),
    ({"frame": "device/local"}, SpatialQueryStatus.MODEL_MISMATCH),
])
def test_query_rejects_stale_future_and_mismatched_pose(kwargs, expected):
    active = model()
    result = SpatialQueryEngine(active).evaluate(
        pose(active, **kwargs), now_ns=110, max_age_ns=10,
    )
    assert result.status == expected
    assert result.position_m is None
    assert result.nearest_feature_id is None


def test_query_distinguishes_missing_fix_from_valid_origin():
    active = model()
    engine = SpatialQueryEngine(active)
    missing = engine.evaluate(None, now_ns=100)
    origin = engine.evaluate(pose(active, position=(0, 0, 0)), now_ns=100)
    assert missing.status == SpatialQueryStatus.NO_FIX
    assert missing.position_m is None
    assert origin.status == SpatialQueryStatus.OK
    assert origin.position_m == (0.0, 0.0, 0.0)


def test_degraded_or_over_threshold_pose_keeps_estimate_but_labels_it():
    active = model()
    engine = SpatialQueryEngine(active)
    degraded = engine.evaluate(
        pose(active, state=PoseState.DEGRADED, uncertainty=0.2), now_ns=110,
    )
    uncertain = engine.evaluate(
        pose(active, uncertainty=6.0), now_ns=110, max_uncertainty_m=5.0,
    )
    assert degraded.status == SpatialQueryStatus.DEGRADED
    assert degraded.nearest_feature_id == "entry"
    assert uncertain.status == SpatialQueryStatus.DEGRADED
    assert "quality threshold" in uncertain.reason


def test_query_validates_thresholds_and_radius():
    active = model()
    engine = SpatialQueryEngine(active)
    with pytest.raises(ValueError):
        engine.evaluate(None, now_ns=-1)
    with pytest.raises(ValueError):
        engine.evaluate(None, now_ns=1, max_uncertainty_m=float("inf"))
    with pytest.raises(ValueError):
        engine.evaluate(None, now_ns=1, nearby_radius_m=-1)
