import pytest

from vigil.blueprint import PoseEstimate, PoseState, register_blueprint
from vigil.spatial_query import SpatialQueryStatus
from vigil.spatial_regions import SpatialRegion, query_region


def model():
    return register_blueprint(
        "building", "r1", frame_id="building/world", units="m",
        features=[{"feature_id": "origin", "label": "Origin", "position": [0, 0, 0]}],
    )


def region(active):
    return SpatialRegion(
        "restricted-lab", "Restricted lab", active.model_id, active.revision,
        active.frame_id, ((0, 0), (5, 0), (5, 5), (0, 5)),
        min_z_m=0, max_z_m=3, level="L1", zone="restricted",
    )


def pose(active, position, *, timestamp=100, state=PoseState.TRACKING, uncertainty=0.2):
    return PoseEstimate(
        active.model_id, active.revision, active.frame_id, position,
        state, uncertainty, timestamp, provenance=("calibrated-test",),
    )


def test_region_contains_interior_boundary_and_respects_height():
    active = model()
    target = region(active)
    assert target.contains((2, 2, 1))
    assert target.contains((0, 2, 1))
    assert not target.contains((6, 2, 1))
    assert not target.contains((2, 2, 4))


def test_region_query_reports_membership_with_quality_status():
    active = model()
    result = query_region(active, pose(active, (2, 2, 1)), region(active), now_ns=110)
    assert result.status == SpatialQueryStatus.OK
    assert result.inside is True
    outside = query_region(active, pose(active, (8, 2, 1)), region(active), now_ns=110)
    assert outside.inside is False


@pytest.mark.parametrize("timestamp,expected", [
    (1, SpatialQueryStatus.STALE),
    (111, SpatialQueryStatus.FUTURE_TIMESTAMP),
])
def test_region_query_never_guesses_membership_for_stale_or_future_pose(timestamp, expected):
    active = model()
    result = query_region(
        active, pose(active, (2, 2, 1), timestamp=timestamp), region(active),
        now_ns=110, max_age_ns=10,
    )
    assert result.status == expected
    assert result.inside is None


def test_region_query_handles_no_fix_model_mismatch_and_degraded_pose():
    active = model()
    target = region(active)
    assert query_region(active, None, target, now_ns=100).status == SpatialQueryStatus.NO_FIX
    wrong = SpatialRegion(
        "other", "Other", "other-model", "r1", "other/frame",
        ((0, 0), (1, 0), (1, 1)), 0, 1,
    )
    assert query_region(active, pose(active, (0, 0, 0)), wrong, now_ns=100).status == SpatialQueryStatus.MODEL_MISMATCH
    degraded = query_region(
        active, pose(active, (2, 2, 1), state=PoseState.DEGRADED), target, now_ns=100,
    )
    assert degraded.status == SpatialQueryStatus.DEGRADED
    assert degraded.inside is True


def test_region_rejects_invalid_geometry_and_query_thresholds():
    active = model()
    with pytest.raises(ValueError):
        SpatialRegion("bad", "Bad", active.model_id, active.revision, active.frame_id, ((0, 0), (1, 1), (2, 2)), 0, 1)
    with pytest.raises(ValueError):
        query_region(active, None, region(active), now_ns=1, max_age_ns=-1)

def test_region_normalizes_closed_polygon_rings_and_rejects_self_intersections():
    active = model()
    closed = SpatialRegion(
        "closed-ring", "Closed ring", active.model_id, active.revision, active.frame_id,
        ((0, 0), (4, 0), (4, 4), (0, 4), (0, 0)), 0, 2,
    )
    assert len(closed.polygon_xy_m) == 4
    assert closed.contains((2, 2, 1))

    with pytest.raises(ValueError, match="self-intersect"):
        SpatialRegion(
            "bow-tie", "Bow tie", active.model_id, active.revision, active.frame_id,
            ((0, 0), (4, 4), (0, 4), (4, 0)), 0, 2,
        )


def test_region_rejects_repeated_vertices_and_invalid_level_zone():
    active = model()
    with pytest.raises(ValueError, match="repeat vertices"):
        SpatialRegion(
            "repeated", "Repeated", active.model_id, active.revision, active.frame_id,
            ((0, 0), (4, 0), (4, 4), (0, 4), (4, 0)), 0, 2,
        )
    with pytest.raises(ValueError, match="level"):
        SpatialRegion(
            "invalid-level", "Invalid", active.model_id, active.revision, active.frame_id,
            ((0, 0), (1, 0), (1, 1)), 0, 2, level="   ",
        )

