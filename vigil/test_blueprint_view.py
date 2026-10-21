import pytest

from vigil.blueprint import PoseEstimate, PoseState, register_blueprint
from vigil.blueprint_view import build_blueprint_view


def model():
    return register_blueprint(
        "building", "r7", frame_id="building/local", units="m",
        features=[
            {"feature_id": "a", "label": "Entry", "position": [0, 0, 0],
             "level": "L1", "zone": "south"},
            {"feature_id": "b", "label": "Stairs", "position": [10, 4, 0],
             "level": "L1", "zone": "core"},
            {"feature_id": "c", "label": "Roof", "position": [100, 100, 20],
             "level": "L2", "zone": "roof"},
        ],
    )


def tracking_pose(m, position=(2, 1, 0)):
    return PoseEstimate(
        m.model_id, m.revision, m.frame_id, position, PoseState.TRACKING,
        0.25, 100, ("uwb-1", "vision-1"),
    )


def test_view_projects_features_and_pose_to_normalized_coordinates():
    m = model()
    view = build_blueprint_view(m, tracking_pose(m), selected_level="L1")
    assert [feature.feature_id for feature in view.features] == ["a", "b"]
    assert view.bounds_m[0].minimum == 0
    assert view.bounds_m[0].maximum == 10
    assert view.features[0].normalized_position == (0.0, 0.0, 0.5)
    assert view.features[1].normalized_position == (1.0, 1.0, 0.5)
    assert view.pose is not None
    assert view.pose.normalized_position == (0.2, 0.25, 0.5)
    assert view.pose.state == "TRACKING"
    assert view.source_sha256 == m.source_sha256


def test_view_keeps_unleveled_features_and_all_levels_when_unfiltered():
    view = build_blueprint_view(model())
    assert {feature.feature_id for feature in view.features} == {"a", "b", "c"}


def test_view_raises_when_selected_level_has_no_visible_geometry():
    with pytest.raises(ValueError, match="no visible features"):
        build_blueprint_view(model(), selected_level="L99")


def test_view_rejects_pose_from_another_revision_or_frame():
    m = model()
    mismatched = PoseEstimate(
        m.model_id, "old-revision", m.frame_id, (0, 0, 0),
        PoseState.TRACKING, 0.1, 100, ("sensor",),
    )
    with pytest.raises(ValueError, match="must match"):
        build_blueprint_view(m, mismatched)


def test_pose_outside_blueprint_bounds_remains_outside_normalized_range():
    m = model()
    view = build_blueprint_view(m, tracking_pose(m, (20, 2, 0)), selected_level="L1")
    assert view.pose is not None
    assert view.pose.normalized_position[0] == 2.0


def test_single_point_axes_are_centered_without_division_by_zero():
    m = register_blueprint(
        "point", "r1", frame_id="point/local", units="m",
        features=[{"feature_id": "p", "label": "Point", "position": [3, 4, 5]}],
    )
    view = build_blueprint_view(m)
    assert view.features[0].normalized_position == (0.5, 0.5, 0.5)
