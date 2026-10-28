"""End-to-end trusted simulation bridge tests for artifact sinking."""
from vigil.artifact_simulation_bridge import ArtifactSimulationBridge
from vigil.historical_artifact_catalog import build_artifact_catalog
from vigil.historical_artifact_store import HistoricalArtifactStore
from vigil.sinking_event_registry import SinkingEventRegistry


def test_confirmed_simulation_sinking_drops_artifacts_at_actual_coordinates(tmp_path):
    catalog = build_artifact_catalog()
    artifacts = HistoricalArtifactStore(catalog, tmp_path / "artifacts.sqlite3")
    sinks = SinkingEventRegistry(tmp_path / "sinks.sqlite3")
    bridge = ArtifactSimulationBridge(artifact_store=artifacts, sinking_registry=sinks)
    artifact = catalog[0]
    carrier = {"id": "UUV-01", "crewId": "crew-alpha", "unitType": "submersible",
               "x": artifact["x"], "y": artifact["y"], "afloat": True,
               "lockedArtifactContainer": {"locked": True, "artifactIds": []}}
    artifacts.discover("PELAGOS-01", artifact["id"])
    artifacts.collect("PELAGOS-01", artifact["id"], "UUV-01", carrier)

    sink_x, sink_y = 0.413, 0.627
    event = {"kind": "UNIT_SUNK", "status": "CONFIRMED", "event_id": "sink-01",
             "unit_id": "UUV-01", "x": sink_x, "y": sink_y}
    sunk_unit = {**carrier, "x": sink_x, "y": sink_y, "afloat": False}
    dropped = bridge.on_unit_sunk("PELAGOS-01", event, sunk_unit)
    assert len(dropped) == 1
    assert dropped[0]["status"] == "LOST"
    assert dropped[0]["location"] == {"x": sink_x, "y": sink_y}
    assert dropped[0]["carrierId"] == ""
    assert artifacts.events("PELAGOS-01", artifact["id"])[-1]["action"] == "SINK_DROP"

    # Duplicate delivery of the same confirmed event cannot clone or respawn it.
    assert bridge.on_unit_sunk("PELAGOS-01", event, sunk_unit) == []
    inventory = artifacts.inventory("PELAGOS-01")
    assert len([item for item in inventory if item["id"] == artifact["id"]]) == 1
    assert inventory[0]["location"] == {"x": sink_x, "y": sink_y}
    artifacts.close()
    sinks.close()


def test_bridge_rejects_unconfirmed_sink_without_dropping_artifact(tmp_path):
    catalog = build_artifact_catalog()
    artifacts = HistoricalArtifactStore(catalog, tmp_path / "artifacts.sqlite3")
    sinks = SinkingEventRegistry()
    bridge = ArtifactSimulationBridge(artifact_store=artifacts, sinking_registry=sinks)
    with __import__("pytest").raises(ValueError, match="confirmed UNIT_SUNK"):
        bridge.on_unit_sunk("PELAGOS-01", {"kind": "UNIT_SUNK", "status": "INDICATED",
            "event_id": "sink-02", "unit_id": "UUV-01", "x": 0.4, "y": 0.6},
            {"id": "UUV-01", "crewId": "crew-alpha", "unitType": "submersible",
             "afloat": False, "x": 0.4, "y": 0.6})
    assert all(item["status"] == "UNDISCOVERED" for item in artifacts.inventory("PELAGOS-01"))
    artifacts.close()
    sinks.close()

def test_coreless_replay_sink_event_routes_through_trusted_bridge(tmp_path):
    from vigil.provenance import EventProvenance
    from vigil.simulation import ReplayEvent

    catalog = build_artifact_catalog()
    artifacts = HistoricalArtifactStore(catalog, tmp_path / "artifacts.sqlite3")
    sinks = SinkingEventRegistry(tmp_path / "sinks.sqlite3")
    bridge = ArtifactSimulationBridge(artifact_store=artifacts, sinking_registry=sinks)
    artifact = catalog[0]
    carrier = {"id": "UUV-REPLAY", "crewId": "crew-alpha", "unitType": "submersible",
               "x": artifact["x"], "y": artifact["y"], "afloat": True,
               "lockedArtifactContainer": {"locked": True, "artifactIds": []}}
    artifacts.discover("PELAGOS-01", artifact["id"])
    artifacts.collect("PELAGOS-01", artifact["id"], "UUV-REPLAY", carrier)
    sink_x, sink_y = 0.61, 0.73
    replay = ReplayEvent(
        event_id="replay-sink-01",
        timestamp_ns=1234,
        kind="UNIT_SUNK",
        payload={"status": "CONFIRMED", "unit_id": "UUV-REPLAY", "x": sink_x, "y": sink_y},
        provenance=EventProvenance(
            source_type="simulation", source_ids=("UUV-REPLAY",),
            timestamp_ns=1234, confidence=0.99,
        ),
    )
    dropped = bridge.on_replay_event(
        "PELAGOS-01", replay,
        {**carrier, "x": sink_x, "y": sink_y, "afloat": False},
    )
    assert dropped[0]["location"] == {"x": sink_x, "y": sink_y}
    assert dropped[0]["status"] == "LOST"
    artifacts.close()
    sinks.close()


def test_replay_sink_event_requires_simulation_provenance(tmp_path):
    from vigil.simulation import ReplayEvent
    artifacts = HistoricalArtifactStore(build_artifact_catalog(), tmp_path / "artifacts.sqlite3")
    sinks = SinkingEventRegistry()
    bridge = ArtifactSimulationBridge(artifact_store=artifacts, sinking_registry=sinks)
    replay = ReplayEvent(
        event_id="untrusted-sink", timestamp_ns=1, kind="UNIT_SUNK",
        payload={"status": "CONFIRMED", "unit_id": "UUV-01", "x": 0.4, "y": 0.6},
    )
    with __import__("pytest").raises(ValueError, match="simulation provenance"):
        bridge.on_replay_event("PELAGOS-01", replay, {})
    artifacts.close()
    sinks.close()
