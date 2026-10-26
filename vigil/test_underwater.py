from vigil.underwater import (
    SonarMode, SonarSensor, UnderwaterTarget, render_sonar_terminal, simulate_sonar_sweep,
)


def sensor(mode=SonarMode.ACTIVE):
    return SonarSensor("sonar-1", mode, max_range_m=5000, sensitivity=1.0,
                       environmental_noise=0.0, range_uncertainty_fraction=0.05)


def target():
    return UnderwaterTarget("hidden-sub-1", 1000, 0, 200, acoustic_signature=1.0, moving=True)


def test_sonar_generates_repeatable_contact_without_exposing_hidden_truth():
    first = simulate_sonar_sweep(sensor(), [target()], sensor_position_m=(0, 0), timestamp_ns=10)
    second = simulate_sonar_sweep(sensor(), [target()], sensor_position_m=(0, 0), timestamp_ns=10)
    assert first == second
    assert first.targets_considered == 1
    assert len(first.contacts) == 1
    contact = first.contacts[0]
    assert contact.estimated_range_m > 0
    assert 0 <= contact.confidence <= 1
    assert not hasattr(contact, "target_id")
    assert not hasattr(contact, "x_m")


def test_sonar_misses_targets_outside_configured_range():
    short = SonarSensor("short", SonarMode.ACTIVE, max_range_m=100, sensitivity=1.0,
                        environmental_noise=0.0)
    sweep = simulate_sonar_sweep(short, [target()], sensor_position_m=(0, 0), timestamp_ns=1)
    assert not sweep.contacts
    assert sweep.detections_missed == 1


def test_active_and_passive_sonar_are_distinct_sensor_modes():
    active = simulate_sonar_sweep(sensor(SonarMode.ACTIVE), [target()],
                                  sensor_position_m=(0, 0), timestamp_ns=12)
    passive = simulate_sonar_sweep(sensor(SonarMode.PASSIVE), [target()],
                                   sensor_position_m=(0, 0), timestamp_ns=12)
    assert active.mode is SonarMode.ACTIVE
    assert passive.mode is SonarMode.PASSIVE
    assert active.contacts[0].mode is SonarMode.ACTIVE
    assert passive.contacts[0].mode is SonarMode.PASSIVE


def test_terminal_renders_estimated_sensor_returns_not_hidden_target_identity():
    sweep = simulate_sonar_sweep(sensor(), [target()], sensor_position_m=(0, 0), timestamp_ns=10)
    output = render_sonar_terminal(sweep)
    assert "SONAR sonar-1" in output
    assert "range~" in output
    assert "hidden-sub-1" not in output


def test_invalid_environment_noise_is_rejected():
    try:
        simulate_sonar_sweep(sensor(), [target()], sensor_position_m=(0, 0),
                             timestamp_ns=1, sea_state_noise=1.1)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid sea-state noise was accepted")


def test_sonar_sweep_flows_into_normalized_sensor_event_ledger_without_truth_leak():
    from vigil.sensor_event import SensorEventLedger
    from vigil.underwater import append_sonar_sweep_to_ledger

    sweep = simulate_sonar_sweep(sensor(), [target()], sensor_position_m=(0, 0), timestamp_ns=25)
    ledger = SensorEventLedger()
    assert append_sonar_sweep_to_ledger(sweep, ledger) == 1
    events = ledger.snapshot(now_ns=25)
    assert len(events) == 1
    event = events[0]
    assert event.modality == "acoustic_sonar"
    assert event.event_kind == "sonar_contact"
    assert event.calibration_status == "simulation_only"
    assert event.uncertainty_m is not None
    assert "hidden-sub-1" not in str(event.to_dict())
    assert "x_m" not in event.to_dict()


def test_empty_sonar_sweep_is_still_recorded_as_context():
    from vigil.sensor_event import SensorEventLedger, SensorEventStatus
    from vigil.underwater import append_sonar_sweep_to_ledger

    short = SonarSensor("short", SonarMode.ACTIVE, max_range_m=10, sensitivity=1.0,
                        environmental_noise=0.0)
    sweep = simulate_sonar_sweep(short, [target()], sensor_position_m=(0, 0), timestamp_ns=26)
    ledger = SensorEventLedger()
    assert append_sonar_sweep_to_ledger(sweep, ledger) == 1
    events = ledger.snapshot(now_ns=26)
    assert len(events) == 1
    assert events[0].event_kind == "sonar_sweep_no_contact"
    assert events[0].status is SensorEventStatus.CONTEXT
