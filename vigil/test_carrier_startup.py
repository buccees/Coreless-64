"""Carrier startup integration tests for persistent VIGIL state."""
from vigil.blueprint import register_blueprint
from vigil.carrier_startup import open_carrier_spatial_workspace
from vigil.spatial_registry_store import SpatialRegistryStore


def test_carrier_startup_restores_active_spatial_registry_and_sensor_history(tmp_path):
    database = tmp_path / "CORELESS_STATE" / "vigil-spatial.sqlite3"
    model = register_blueprint(
        "carrier-site", "r1", frame_id="carrier-site/world", units="m",
        features=[{"feature_id": "origin", "label": "Origin",
                   "position": [0, 0, 0], "level": "L1"}],
    )
    store = SpatialRegistryStore(str(database))
    try:
        store.save_model(model, activate=True)
        store.append_sensor_lifecycle_event({
            "provider_id": "uwb-array", "state": "ONLINE",
            "timestamp_ns": "100", "consecutive_failures": 0,
            "last_success_ns": "100", "error": None,
        })
        store.set_sensor_alert_acknowledgement(
            "coverage:uwb-array:cart-zone:STALE_REPORT",
            acknowledged=True, acknowledged_at_utc="2026-10-23T12:00:00Z",
            acknowledged_by="integration-test",
        )
    finally:
        store.close()

    restored_store, workspace = open_carrier_spatial_workspace(database)
    try:
        assert workspace.active_model == model
        assert workspace.object_tracks == ()
        assert restored_store.load_sensor_lifecycle_events() == ({
            "provider_id": "uwb-array", "state": "ONLINE",
            "timestamp_ns": "100", "consecutive_failures": 0,
            "last_success_ns": "100", "error": None,
        },)
        assert restored_store.load_sensor_alert_acknowledgements()[
            "coverage:uwb-array:cart-zone:STALE_REPORT"
        ]["acknowledged_by"] == "integration-test"
    finally:
        restored_store.close()
