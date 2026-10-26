from vigil.blueprint import PoseEstimate, PoseState, register_blueprint
from vigil.positioning import SpatialObservation
from vigil.object_tracking import ObjectTrack
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



def test_terminal_surfaces_object_track_conflicts_and_sensor_sources():
    model = fixture_model()
    track = ObjectTrack(
        object_id="person-7", model_id=model.model_id, model_revision=model.revision,
        frame_id=model.frame_id, position_m=(1.0, 2.0, 0.0),
        velocity_mps=(0.0, 0.0, 0.0), uncertainty_m=0.2, last_seen_ns=10,
        sensor_ids=("camera-1", "thermal-1"), modalities=("infrared", "vision"),
        observation_count=2, association_id="entity-7",
        provenance=("thermal-detector", "vision-reid"), conflict=True,
        conflict_reasons=("position_disagreement",),
        conflicting_sensor_ids=("camera-1", "thermal-1"),
    )
    output = VigilTerminal(color=False).render(
        model, fixture_pose(model), [], now_ns=20, object_tracks=(track,)
    )
    assert "OBJECT TRACKING" in output
    assert "person-7: CONFLICT position_disagreement" in output
    assert "conflicting sensors: camera-1, thermal-1" in output

def test_terminal_displays_motion_only_when_track_has_a_timestamped_baseline():
    model = fixture_model()
    unknown = ObjectTrack(
        object_id="new-target", model_id=model.model_id, model_revision=model.revision,
        frame_id=model.frame_id, position_m=(1, 2, 0), velocity_mps=(0, 0, 0),
        uncertainty_m=0.2, last_seen_ns=20, sensor_ids=("uwb",), modalities=("uwb",),
        observation_count=1, position_history_m=((20, (1, 2, 0)),),
    )
    moving = ObjectTrack(
        object_id="moving-cart", model_id=model.model_id, model_revision=model.revision,
        frame_id=model.frame_id, position_m=(2, 2, 0), velocity_mps=(0.2, 0, 0),
        uncertainty_m=0.2, last_seen_ns=20, sensor_ids=("uwb",), modalities=("uwb",),
        observation_count=2, position_history_m=((10, (1, 2, 0)), (20, (2, 2, 0))),
    )
    stationary = ObjectTrack(
        object_id="stationary-box", model_id=model.model_id, model_revision=model.revision,
        frame_id=model.frame_id, position_m=(3, 2, 0), velocity_mps=(0.01, 0, 0),
        uncertainty_m=0.2, last_seen_ns=20, sensor_ids=("uwb",), modalities=("uwb",),
        observation_count=2, position_history_m=((10, (3, 2, 0)), (20, (3.01, 2, 0))),
    )
    output = VigilTerminal(color=False).render(
        model, fixture_pose(model), [], now_ns=20,
        object_tracks=(unknown, moving, stationary),
    )
    assert "new-target: MOTION UNKNOWN" in output
    assert "moving-cart: MOVING 0.20m/s" in output
    assert "stationary-box: STATIONARY 0.01m/s" in output

def test_terminal_labels_last_known_position_and_never_claims_stale_motion():
    model = fixture_model()
    stale = ObjectTrack(
        object_id="stationary-crate", model_id=model.model_id,
        model_revision=model.revision, frame_id=model.frame_id,
        position_m=(1.0, 2.0, 0.0), velocity_mps=(0.0, 0.0, 0.0),
        uncertainty_m=0.2, last_seen_ns=10, sensor_ids=("uwb-1",),
        modalities=("uwb",), observation_count=2,
        position_history_m=((0, (1.0, 2.0, 0.0)), (10, (1.0, 2.0, 0.0))),
        presence_state="STALE",
    )
    output = VigilTerminal(color=False).render(
        model, fixture_pose(model), now_ns=5_000_000_000,
        object_tracks=(stale,),
    )
    assert "stationary-crate: STALE / LAST KNOWN" in output
    assert "stationary-crate: STATIONARY" not in output
    assert "age=4999ms" in output



def test_main_terminal_renders_authorized_sonar_sweep():
    from vigil.underwater import SonarMode, SonarSensor, UnderwaterTarget, simulate_sonar_sweep

    model = fixture_model()
    sweep = simulate_sonar_sweep(
        SonarSensor("sonar-ui", SonarMode.PASSIVE, 5000, sensitivity=1.0,
                    environmental_noise=0.0),
        [UnderwaterTarget("secret-sub-id", 900, 0, 100, acoustic_signature=1.0)],
        sensor_position_m=(0, 0),
        timestamp_ns=10,
    )
    output = VigilTerminal(color=False).render(
        model, fixture_pose(model), now_ns=10, sonar_sweeps=[sweep]
    )
    assert "UNDERWATER / SONAR" in output
    assert "sonar-ui PASSIVE" in output
    assert "range~" in output
    assert "secret-sub-id" not in output


def test_main_terminal_marks_old_sonar_sweep_stale():
    from vigil.underwater import SonarMode, SonarSensor, UnderwaterTarget, simulate_sonar_sweep

    model = fixture_model()
    sweep = simulate_sonar_sweep(
        SonarSensor("sonar-old", SonarMode.ACTIVE, 5000, sensitivity=1.0,
                    environmental_noise=0.0),
        [UnderwaterTarget("secret-sub-old", 900, 0, 100, acoustic_signature=1.0)],
        sensor_position_m=(0, 0),
        timestamp_ns=10,
    )
    output = VigilTerminal(color=False).render(
        model, fixture_pose(model), now_ns=3_000_000_010, sonar_sweeps=[sweep]
    )
    assert "sonar-old ACTIVE" in output
    assert "STALE" in output
    assert "secret-sub-old" not in output
