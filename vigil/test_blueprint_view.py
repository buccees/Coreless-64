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


from vigil.object_tracking import ObjectTrack


def tracked_object(m, **overrides):
    values = {
        "object_id": "person-7",
        "model_id": m.model_id,
        "model_revision": m.revision,
        "frame_id": m.frame_id,
        "position_m": (3.0, 2.0, 0.2),
        "velocity_mps": (0.1, 0.0, 0.0),
        "uncertainty_m": 0.4,
        "last_seen_ns": 500,
        "sensor_ids": ("uwb-1", "ir-2"),
        "modalities": ("infrared", "uwb"),
        "observation_count": 4,
        "association_id": "entity-7",
        "provenance": ("calibrated-uwb", "thermal-detector"),
        "conflict": True,
        "conflict_reasons": ("position_disagreement",),
        "conflicting_sensor_ids": ("ir-2", "uwb-1"),
    }
    values.update(overrides)
    return ObjectTrack(**values)


def test_view_projects_track_identity_uncertainty_and_conflict_for_renderer():
    m = model()
    track = tracked_object(m)
    view = build_blueprint_view(m, selected_level="L1", object_tracks=(track,))
    assert len(view.objects) == 1
    marker = view.objects[0]
    assert marker.position_m == track.position_m
    assert marker.normalized_position == (0.3, 0.5, 0.5)
    assert marker.association_id == "entity-7"
    assert marker.uncertainty_m == 0.4
    assert marker.conflict is True
    assert marker.conflict_reasons == ("position_disagreement",)
    assert marker.conflicting_sensor_ids == ("ir-2", "uwb-1")
    assert marker.sensor_ids == ("uwb-1", "ir-2")
    assert marker.modalities == ("infrared", "uwb")
    assert marker.provenance == ("calibrated-uwb", "thermal-detector")


def test_view_ignores_tracks_from_wrong_model_revision_or_frame():
    m = model()
    bad_tracks = (
        tracked_object(m, model_revision="old"),
        tracked_object(m, frame_id="other-frame"),
        tracked_object(m, model_id="other-building"),
    )
    view = build_blueprint_view(m, object_tracks=bad_tracks)
    assert view.objects == ()


def test_view_uses_surveyed_floor_elevations_without_guessing_when_unavailable():
    m = register_blueprint(
        "building", "r1", frame_id="building/frame", units="m",
        features=[
            {"feature_id": "a", "label": "L1", "position": [0, 0, 0], "level": "L1"},
            {"feature_id": "b", "label": "L2", "position": [10, 10, 4], "level": "L2"},
        ],
        metadata={"floor_elevations_m": {"L1": 0.0, "L2": 4.0}},
    )
    lower = tracked_object(m, position_m=(1.0, 1.0, 0.2))
    upper = tracked_object(m, object_id="person-8", position_m=(1.0, 1.0, 4.1), conflict=False, conflict_reasons=(), conflicting_sensor_ids=())
    view = build_blueprint_view(m, selected_level="L1", object_tracks=(lower, upper))
    assert view.objects[0].inferred_level == "L1"
    assert view.objects[0].visible_on_selected_level is True
    assert view.objects[1].inferred_level == "L2"
    assert view.objects[1].visible_on_selected_level is False

    no_elevations = model()
    unknown = build_blueprint_view(no_elevations, selected_level="L1", object_tracks=(tracked_object(no_elevations),))
    assert unknown.objects[0].inferred_level is None
    assert unknown.objects[0].visible_on_selected_level is None


def test_view_exposes_timestamped_motion_trail_and_falls_back_for_legacy_tracks():
    m = model()
    track = tracked_object(
        m, position_history_m=((400, (2.0, 2.0, 0.0)), (500, (3.0, 2.0, 0.2)))
    )
    view = build_blueprint_view(m, selected_level="L1", object_tracks=(track,))
    assert view.objects[0].motion_trail_m == track.position_history_m
    legacy = tracked_object(m, position_history_m=())
    legacy_view = build_blueprint_view(m, object_tracks=(legacy,))
    assert legacy_view.objects[0].motion_trail_m == ((legacy.last_seen_ns, legacy.position_m),)

def test_view_marks_candidate_floor_transitions_from_timestamped_history():
    m = register_blueprint(
        "building", "r1", frame_id="building/frame", units="m",
        features=[
            {"feature_id": "a", "label": "L1", "position": [0, 0, 0], "level": "L1"},
            {"feature_id": "b", "label": "L2", "position": [10, 10, 4], "level": "L2"},
        ],
        metadata={"floor_elevations_m": {"L1": 0.0, "L2": 4.0}},
    )
    track = tracked_object(
        m,
        position_m=(3.0, 2.0, 4.1),
        position_history_m=(
            (100, (1.0, 1.0, 0.2)),
            (200, (2.0, 1.0, 0.5)),
            (300, (3.0, 2.0, 4.1)),
            (400, (4.0, 2.0, 3.9)),
        ),
        position_history_sensor_ids=(
            (100, ("uwb-entry",)),
            (200, ("uwb-entry", "vision-east")),
            (300, ("infrared-stair",)),
            (400, ("infrared-stair", "uwb-roof")),
        ),
    )
    view = build_blueprint_view(m, object_tracks=(track,))
    transitions = view.objects[0].floor_transitions
    assert len(transitions) == 1
    assert transitions[0].timestamp_ns == 300
    assert transitions[0].from_level == "L1"
    assert transitions[0].to_level == "L2"
    assert transitions[0].from_elevation_m == 0.0
    assert transitions[0].to_elevation_m == 4.0
    assert transitions[0].from_sensor_ids == ("uwb-entry", "vision-east")
    assert transitions[0].to_sensor_ids == ("infrared-stair",)



def test_view_ignores_single_sample_floor_spike():
    m = register_blueprint(
        "building", "r1", frame_id="building/frame", units="m",
        features=[
            {"feature_id": "a", "label": "L1", "position": [0, 0, 0], "level": "L1"},
            {"feature_id": "b", "label": "L2", "position": [10, 10, 4], "level": "L2"},
        ],
        metadata={"floor_elevations_m": {"L1": 0.0, "L2": 4.0}},
    )
    track = tracked_object(
        m,
        position_m=(3.0, 2.0, 0.2),
        position_history_m=(
            (100, (1.0, 1.0, 0.1)),
            (200, (2.0, 1.0, 4.1)),
            (300, (3.0, 2.0, 0.2)),
        ),
    )
    view = build_blueprint_view(m, object_tracks=(track,))
    assert view.objects[0].floor_transitions == ()

def test_view_does_not_infer_floor_transition_from_unknown_height_samples():
    m = register_blueprint(
        "building", "r1", frame_id="building/frame", units="m",
        features=[
            {"feature_id": "a", "label": "L1", "position": [0, 0, 0], "level": "L1"},
            {"feature_id": "b", "label": "L2", "position": [10, 10, 4], "level": "L2"},
        ],
        metadata={"floor_elevations_m": {"L1": 0.0, "L2": 4.0}},
    )
    track = tracked_object(
        m,
        position_history_m=((100, (1.0, 1.0, 0.2)), (200, (2.0, 2.0, 2.0)), (300, (3.0, 2.0, 4.1))),
    )
    view = build_blueprint_view(m, object_tracks=(track,))
    assert view.objects[0].floor_transitions == ()

