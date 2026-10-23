"""Carrier startup integration tests for persistent VIGIL state."""
from vigil.blueprint import register_blueprint
from vigil.object_tracking import ObjectObservation, ObjectTrack, TrackingModality
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
    raw = ObjectObservation(
        object_id="cart-7", sensor_id="uwb-array", model_id=model.model_id,
        model_revision=model.revision, frame_id=model.frame_id,
        timestamp_ns=100, position_m=(1.0, 2.0, 0.0), uncertainty_m=0.2,
        modality=TrackingModality.UWB, provenance="restart-test",
        independence_group="uwb-array", calibration_status="verified",
        calibration_ids=("survey-1",), lineage_declared=True,
    )
    track = ObjectTrack(
        object_id="cart-7", model_id=model.model_id, model_revision=model.revision,
        frame_id=model.frame_id, position_m=(1.0, 2.0, 0.0),
        velocity_mps=(0.0, 0.0, 0.0), uncertainty_m=0.2, last_seen_ns=100,
        sensor_ids=("uwb-array",), modalities=("uwb",), observation_count=1,
        provenance=("restart-test",), independence_groups=("uwb-array",),
        position_history_m=((100, (1.0, 2.0, 0.0)),),
        position_history_sensor_ids=((100, ("uwb-array",)),),
        calibration_status="verified", calibration_ids=("survey-1",),
        lineage_declared=True, presence_state="CURRENT", raw_observations=(raw,),
    )
    try:
        store.save_model(model, activate=True)
        store.save_object_tracks(model, (track,))
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
