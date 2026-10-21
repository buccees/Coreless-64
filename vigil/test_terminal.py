from vigil.blueprint import PoseEstimate, PoseState, register_blueprint
from vigil.positioning import SpatialObservation
from vigil.terminal import VigilTerminal


def fixture_model():
    return register_blueprint(
        "warehouse-a", "rev-7", frame_id="warehouse-local", units="m",
        features=[{"feature_id": "a1", "label": "Dock", "position": [1, 2, 0],
                   "level": "L1", "zone": "DOCK"}],
    )


def fixture_pose(model, state=PoseState.TRACKING):
    return PoseEstimate(model.model_id, model.revision, model.frame_id,
                        (1.2, 2.1, 0.0), state, 0.35, 10,
                        provenance=("gps-1", "uwb-1"))


def test_terminal_renders_blueprint_pose_and_zone_without_ansi():
    model = fixture_model()
    obs = SpatialObservation("obs-1", "uwb", model.model_id, model.revision,
                             model.frame_id, 10, (1.2, 2.1, 0.0), 0.25, "test")
    output = VigilTerminal(color=False).render(model, fixture_pose(model), [obs], now_ns=20)
    assert "V I G I L" in output
    assert "warehouse-a / rev-7" in output
    assert "TRACKING" in output
    assert "DOCK" in output
    assert "ONLINE" in output
    assert "\\033[" not in output


def test_terminal_never_invents_position_when_pose_lost():
    model = fixture_model()
    pose = PoseEstimate(model.model_id, model.revision, model.frame_id,
                        None, PoseState.LOST, None, None, reason="no fresh fix")
    output = VigilTerminal(color=False).render(model, pose, [], now_ns=20)
    assert "TRACKING  : LOST" in output
    assert "POSITION  : X UNKNOWN" in output
    assert "FLOOR/ZONE: UNKNOWN" in output
    assert "No sensor observations received" in output


def test_sensor_rows_mark_old_data_stale_and_ignore_future_observations():
    model = fixture_model()
    old = SpatialObservation("old", "gps", model.model_id, model.revision,
                             model.frame_id, 1, (0, 0, 0), 1.0, "test")
    future = SpatialObservation("future", "future-sensor", model.model_id, model.revision,
                                model.frame_id, 1000, (0, 0, 0), 1.0, "test")
    terminal = VigilTerminal(color=False, max_sensor_age_ns=10)
    rows = terminal.sensor_lines([old, future], now_ns=20)
    assert len(rows) == 1
    assert rows[0].source_id == "gps"
    assert rows[0].state == "STALE"


def test_terminal_does_not_match_pose_from_wrong_model_revision():
    model = fixture_model()
    wrong = PoseEstimate(model.model_id, "old-revision", model.frame_id,
                         (1.2, 2.1, 0), PoseState.DEGRADED, 1.0, 10)
    output = VigilTerminal(color=False).render(model, wrong, [], now_ns=20)
    assert "FLOOR/ZONE: UNKNOWN" in output



def test_terminal_field_sanitization_preserves_digits_and_hides_escape_controls():
    safe = VigilTerminal._fit("L1 floor 2", 20)
    assert safe.startswith("L1 floor 2")
    unsafe = VigilTerminal._fit("A\x1b[31mB", 20)
    assert "\x1b" not in unsafe
    assert unsafe.startswith("A?")
