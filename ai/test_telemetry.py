from ai.telemetry import TelemetryProvider


def test_telemetry_is_read_only_to_consumers():
    telemetry = TelemetryProvider()
    snapshot = telemetry.publish(cpu={"load": 0.5}, memory={"used": 4.0})
    assert snapshot.cpu["load"] == 0.5
    assert telemetry.snapshot() == snapshot


def test_telemetry_replaces_snapshot_deterministically():
    telemetry = TelemetryProvider()
    telemetry.publish(cpu={"load": 0.2})
    snapshot = telemetry.publish(cpu={"load": 0.8}, vms={"vm1": 1.0})
    assert snapshot.cpu == {"load": 0.8}
    assert snapshot.vms == {"vm1": 1.0}
