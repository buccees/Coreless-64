import pytest

from vigil.blueprint import CoordinateTransform, PoseEstimate, PoseState, register_blueprint
from vigil.building import BuildingBlueprintBuilder, FloorTracker, VerticalConnection


def floor(model_id, frame, features):
    return register_blueprint(
        model_id, "r1", frame_id=frame, units="m", features=features
    )


def make_building():
    ground = floor("ground-upload", "ground/local", [
        {"feature_id": "entry", "label": "Entry", "position": [0, 0, 0], "zone": "south"},
        {"feature_id": "stairs", "label": "Stair landing", "position": [5, 5, 0], "zone": "core"},
    ])
    upper = floor("upper-upload", "upper/local", [
        {"feature_id": "stairs", "label": "Stair landing", "position": [0, 0, 0], "zone": "core"},
        {"feature_id": "office", "label": "Office", "position": [8, 5, 0], "zone": "east"},
    ])
    builder = BuildingBlueprintBuilder("building-a", "combined-r1", "building/world")
    builder.add_floor(
        ground, level_id="L1", label="Ground floor", elevation_m=0,
        transform_to_building=CoordinateTransform(
            "ground/local", "building/world", translation=(0, 0, 0), provenance="survey"
        ),
    )
    builder.add_floor(
        upper, level_id="L2", label="Upper floor", elevation_m=3.2,
        transform_to_building=CoordinateTransform(
            "upper/local", "building/world", translation=(5, 5, 3.2), provenance="survey"
        ),
    )
    builder.connect_floors(VerticalConnection(
        "stairs-1-2", "stairs", "L1", "L2",
        (5, 5, 0), (5, 5, 3.2),
    ))
    return builder.build()


def pose(building, position, uncertainty=0.2, state=PoseState.TRACKING):
    model = building.model
    return PoseEstimate(
        model.model_id, model.revision, model.frame_id, position, state,
        uncertainty, 100, ("uwb", "vision"),
    )


def test_upload_time_floor_assignment_composes_shared_building_frame():
    building = make_building()
    assert [floor.level_id for floor in building.floors] == ["L1", "L2"]
    assert {feature.level for feature in building.model.features} == {"L1", "L2"}
    upper_stairs = next(f for f in building.model.features if f.feature_id == "L2:stairs")
    assert upper_stairs.position_m == (5.0, 5.0, 3.2)
    assert building.model.frame_id == "building/world"


def test_floor_selection_is_only_initialization_and_transition_is_automatic():
    building = make_building()
    tracker = FloorTracker(building, confirmations_required=2)
    assert tracker.establish_start("L1") == "L1"
    first = tracker.update(pose(building, (5, 5, 3.1)))
    assert not first.changed
    assert first.candidate_level == "L2"
    second = tracker.update(pose(building, (5, 5, 3.2)))
    assert second.changed
    assert second.active_level == "L2"


def test_floor_tracker_does_not_switch_without_vertical_connection_evidence():
    building = make_building()
    tracker = FloorTracker(building)
    tracker.establish_start("L1")
    result = tracker.update(pose(building, (8, 5, 3.2)))
    assert not result.changed
    assert result.active_level == "L1"


def test_floor_tracker_rejects_pose_from_another_coordinate_frame():
    building = make_building()
    tracker = FloorTracker(building)
    tracker.establish_start("L1")
    wrong = PoseEstimate(
        "building-a", "combined-r1", "ground/local", (5, 5, 3.2),
        PoseState.TRACKING, 0.2, 100, ("sensor",),
    )
    with pytest.raises(ValueError, match="aligned"):
        tracker.update(wrong)


def test_floor_tracker_holds_floor_when_pose_is_lost():
    building = make_building()
    tracker = FloorTracker(building)
    tracker.establish_start("L1")
    result = tracker.update(pose(building, None, state=PoseState.LOST))
    assert result.active_level == "L1"
    assert not result.changed
