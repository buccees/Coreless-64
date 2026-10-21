import pytest

from vigil.blueprint import PoseState, register_blueprint
from vigil.positioning import FakeObservationProvider, PoseEstimator, SpatialObservation


def model():
    return register_blueprint(
        "building-a",
        "rev-3",
        frame_id="building-a/model",
        units="m",
        features=[{"feature_id": "anchor-1", "label": "Anchor", "position": [0, 0, 0]}],
    )


def observation(
    observation_id,
    source_id,
    position=(1.0, 2.0, 0.0),
    *,
    timestamp_ns=10_000,
    model_id="building-a",
    revision="rev-3",
    frame_id="building-a/model",
    uncertainty=0.25,
):
    return SpatialObservation(
        observation_id=observation_id,
        source_id=source_id,
        model_id=model_id,
        model_revision=revision,
        frame_id=frame_id,
        timestamp_ns=timestamp_ns,
        position_m=position,
        uncertainty_m=uncertainty,
        provenance=f"fake:{source_id}",
    )


def test_fake_provider_returns_immutable_observation_batch():
    batch = (observation("o1", "uwb"), observation("o2", "vision"))
    assert FakeObservationProvider(batch).read() == batch


def test_pose_estimator_fuses_fresh_aligned_observations():
    blueprint = model()
    observations = (
        observation("uwb-1", "uwb", (1.0, 2.0, 0.0)),
        observation("vision-1", "vision", (1.1, 2.0, 0.0)),
    )
    pose = PoseEstimator().update(blueprint, observations, now_ns=10_500)
    assert pose.state == PoseState.TRACKING
    assert pose.position_m == pytest.approx((1.05, 2.0, 0.0), abs=0.01)
    assert pose.frame_id == blueprint.frame_id
    assert pose.uncertainty_m is not None
    assert set(pose.provenance) == {"uwb-1", "vision-1"}


def test_pose_estimator_does_not_fabricate_a_fix_from_missing_or_stale_data():
    blueprint = model()
    estimator = PoseEstimator()
    missing = estimator.update(blueprint, (), now_ns=20_000)
    stale = estimator.update(
        blueprint,
        (observation("old", "uwb", timestamp_ns=1),),
        now_ns=20_000,
        max_age_ns=100,
    )
    assert missing.state == PoseState.LOST
    assert missing.position_m is None
    assert stale.state == PoseState.LOST
    assert stale.position_m is None
    assert "stale" in stale.reason


def test_pose_estimator_rejects_wrong_model_revision_or_frame():
    blueprint = model()
    wrong = observation("wrong", "gps", model_id="building-b")
    pose = PoseEstimator().update(blueprint, (wrong,), now_ns=10_500)
    assert pose.state == PoseState.LOST
    assert pose.position_m is None


def test_single_sensor_is_degraded_and_inconsistent_sensors_are_degraded():
    blueprint = model()
    estimator = PoseEstimator()
    single = estimator.update(
        blueprint, (observation("one", "uwb"),), now_ns=10_500
    )
    inconsistent = estimator.update(
        blueprint,
        (
            observation("a", "uwb", (0, 0, 0)),
            observation("b", "vision", (10, 0, 0)),
        ),
        now_ns=10_500,
        max_disagreement_m=1.0,
    )
    assert single.state == PoseState.DEGRADED
    assert inconsistent.state == PoseState.DEGRADED
    assert inconsistent.uncertainty_m > 1.0


def test_spatial_observation_validates_uncertainty_and_timestamp():
    with pytest.raises(ValueError, match="uncertainty"):
        observation("bad", "uwb", uncertainty=0)
    with pytest.raises(ValueError, match="timestamp"):
        observation("bad", "uwb", timestamp_ns=-1)
