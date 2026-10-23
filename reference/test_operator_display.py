import json
import pytest

from operator_display import (
    OperatorAlert,
    OperatorSensorStatus,
    OperatorViewState,
    PROTOCOL_VERSION,
)


def test_operator_view_state_encodes_versioned_remote_snapshot():
    state = OperatorViewState(
        sequence=7,
        generated_at_ns=120,
        source_timestamp_ns=115,
        connection_state="connected",
        runtime_state="ready",
        sensors=(
            OperatorSensorStatus(
                sensor_id="ir-0",
                modality="infrared",
                state="ready",
                source_timestamp_ns=110,
                calibration="verified",
            ),
        ),
        alerts=(
            OperatorAlert(
                alert_id="alert-1",
                severity="warning",
                message="Input age above threshold",
                source="runtime.health",
                source_timestamp_ns=114,
            ),
        ),
    )

    encoded = state.encode()
    decoded = json.loads(encoded)

    assert decoded["protocol_version"] == PROTOCOL_VERSION
    assert decoded["sequence"] == 7
    assert decoded["sensors"][0]["modality"] == "infrared"
    assert decoded["sensors"][0]["calibration"] == "verified"
    assert decoded["alerts"][0]["source"] == "runtime.health"
    assert encoded == state.encode()


def test_operator_view_state_rejects_unknown_protocol_version():
    with pytest.raises(ValueError, match="protocol version"):
        OperatorViewState(
            sequence=0,
            generated_at_ns=1,
            source_timestamp_ns=1,
            connection_state="connected",
            runtime_state="ready",
            protocol_version=99,
        )


def test_operator_view_state_rejects_duplicate_sensor_ids():
    sensor = OperatorSensorStatus("rf-0", "wifi_csi", "ready")
    with pytest.raises(ValueError, match="sensor IDs must be unique"):
        OperatorViewState(
            sequence=0,
            generated_at_ns=1,
            source_timestamp_ns=1,
            connection_state="connected",
            runtime_state="ready",
            sensors=(sensor, sensor),
        )


def test_operator_view_state_rejects_duplicate_alert_ids():
    alert = OperatorAlert("alert-1", "info", "ready", "runtime", 1)
    with pytest.raises(ValueError, match="alert IDs must be unique"):
        OperatorViewState(
            sequence=0,
            generated_at_ns=1,
            source_timestamp_ns=1,
            connection_state="connected",
            runtime_state="ready",
            alerts=(alert, alert),
        )


def test_sensor_state_preserves_unavailable_and_calibration_metadata():
    sensor = OperatorSensorStatus(
        "range-0",
        "calibrated_range",
        "unavailable",
        source_timestamp_ns=None,
        calibration="not_calibrated",
        reason="No recent source event",
    )
    assert sensor.as_dict() == {
        "sensor_id": "range-0",
        "modality": "calibrated_range",
        "state": "unavailable",
        "source_timestamp_ns": None,
        "calibration": "not_calibrated",
        "reason": "No recent source event",
    }


@pytest.mark.parametrize("timestamp", [-1, True, 1.5, "12"])
def test_operator_view_state_rejects_invalid_timestamps(timestamp):
    with pytest.raises(ValueError, match="timestamp"):
        OperatorViewState(
            sequence=0,
            generated_at_ns=timestamp,
            source_timestamp_ns=1,
            connection_state="connected",
            runtime_state="ready",
        )


def test_operator_view_state_rejects_unknown_sensor_modality_state():
    with pytest.raises(ValueError, match="sensor state"):
        OperatorSensorStatus("rf-0", "wifi_csi", "probably_ready")



def test_nanosecond_timestamps_are_decimal_strings_on_wire():
    exact = 1_799_999_999_123_456_789
    state = OperatorViewState(
        sequence=1,
        generated_at_ns=exact,
        source_timestamp_ns=exact - 1,
        connection_state="connected",
        runtime_state="ready",
        sensors=(
            OperatorSensorStatus(
                sensor_id="ir-0",
                modality="infrared",
                state="ready",
                source_timestamp_ns=exact - 2,
            ),
        ),
        alerts=(
            OperatorAlert("a-1", "info", "check", "runtime", exact - 3),
        ),
    )
    decoded = json.loads(state.encode())
    assert decoded["generated_at_ns"] == str(exact)
    assert decoded["source_timestamp_ns"] == str(exact - 1)
    assert decoded["sensors"][0]["source_timestamp_ns"] == str(exact - 2)
    assert decoded["alerts"][0]["source_timestamp_ns"] == str(exact - 3)
