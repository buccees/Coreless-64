from vigil.model import Detection, EntityType, Provenance
from vigil.priority import PriorityContext
from vigil.runtime import VigilEnvironment
from vigil.spatial import CameraFrame


class FakeCamera:
    def __init__(self):
        self.frames = [
            CameraFrame("cam", 100, 1, 640, 480),
        ]
    def available(self):
        return bool(self.frames)
    def read(self):
        return self.frames.pop(0) if self.frames else None


class Provider:
    def detect(self, frame):
        return (
            Detection(
                "d1",
                f"{frame.source_id}:{frame.sequence}",
                EntityType.OBJECT,
                "target",
                frame.timestamp_ns,
                position=(1.0, 0.0, 0.0),
                confidence=1.0,
                provenance=(Provenance(frame.source_id, "camera", frame.timestamp_ns),),
            ),
        )


def test_camera_cycle_drives_perception_priority_attention_and_presentation():
    environment = VigilEnvironment(enabled=True, camera=FakeCamera())
    result = environment.run_camera_cycle(
        provider=Provider(),
        priority_context=PriorityContext(100, reference_position=(0.0, 0.0, 0.0)),
    )

    assert result is not None
    assert result.frame_sequence == 1
    assert result.perception is not None
    assert len(result.priority) == 1
    assert result.priority[0].world_entity_id == "d1"
    assert len(result.attention) == 1
    assert result.attention[0].world_entity_id == "d1"
    assert result.presentation is not None
    assert result.presentation.items[0].world_entity_id == "d1"


def test_camera_cycle_still_works_without_perception_provider():
    environment = VigilEnvironment(enabled=True, camera=FakeCamera())
    result = environment.run_camera_cycle()

    assert result is not None
    assert result.perception is None
    assert result.priority == ()
    assert result.attention == ()
    assert result.presentation is not None


def test_camera_cycle_records_complete_derived_pipeline_in_replay():
    environment = VigilEnvironment(enabled=True, camera=FakeCamera())
    environment.run_camera_cycle(
        provider=Provider(),
        priority_context=PriorityContext(100, reference_position=(0.0, 0.0, 0.0)),
    )
    kinds = tuple(event.kind for event in environment.replay.replay())
    assert kinds == (
        "camera.frame",
        "camera.perception",
        "world.state",
        "vigil.priority",
        "vigil.attention",
        "vigil.presentation",
    )


def test_environment_live_replay_drops_artifact_at_authoritative_sink_position(tmp_path):
    from vigil.artifact_simulation_bridge import ArtifactSimulationBridge
    from vigil.historical_artifact_catalog import build_artifact_catalog
    from vigil.historical_artifact_store import HistoricalArtifactStore
    from vigil.provenance import EventProvenance
    from vigil.simulation import ReplayEvent
    from vigil.sinking_event_registry import SinkingEventRegistry

    catalog = build_artifact_catalog()
    store = HistoricalArtifactStore(catalog, tmp_path / "artifacts.sqlite3")
    sinks = SinkingEventRegistry(tmp_path / "sinks.sqlite3")
    bridge = ArtifactSimulationBridge(artifact_store=store, sinking_registry=sinks)
    artifact = catalog[0]
    carrier = {
        "id": "UUV-RUNTIME", "crewId": "crew-alpha", "unitType": "submersible",
        "x": artifact["x"], "y": artifact["y"], "afloat": True,
        "lockedArtifactContainer": {"locked": True, "artifactIds": []},
    }
    store.discover("PELAGOS-01", artifact["id"])
    store.collect("PELAGOS-01", artifact["id"], "UUV-RUNTIME", carrier)
    sink_x, sink_y = 0.418, 0.629
    authoritative_state = {**carrier, "x": sink_x, "y": sink_y, "afloat": False}

    environment = VigilEnvironment(enabled=True)
    environment.configure_artifact_recovery(
        world_seed="PELAGOS-01",
        bridge=bridge,
        resolve_unit_state=lambda unit_id: authoritative_state if unit_id == "UUV-RUNTIME" else None,
    )
    environment.replay.append(ReplayEvent(
        event_id="runtime-sink-01",
        timestamp_ns=500,
        kind="UNIT_SUNK",
        payload={"status": "CONFIRMED", "unit_id": "UUV-RUNTIME", "x": sink_x, "y": sink_y},
        provenance=EventProvenance(
            source_type="simulation", source_ids=("UUV-RUNTIME",),
            timestamp_ns=500, confidence=0.99,
        ),
    ))
    item = next(row for row in store.inventory("PELAGOS-01") if row["id"] == artifact["id"])
    assert item["status"] == "LOST"
    assert item["location"] == {"x": sink_x, "y": sink_y}

    environment.disable_artifact_recovery()
    store.close()
    sinks.close()


def test_confirm_unit_sunk_publishes_server_coordinates_to_artifact_recovery(tmp_path):
    from vigil.artifact_simulation_bridge import ArtifactSimulationBridge
    from vigil.historical_artifact_catalog import build_artifact_catalog
    from vigil.historical_artifact_store import HistoricalArtifactStore
    from vigil.sinking_event_registry import SinkingEventRegistry

    catalog = build_artifact_catalog()
    store = HistoricalArtifactStore(catalog, tmp_path / "artifacts.sqlite3")
    sinks = SinkingEventRegistry(tmp_path / "sinks.sqlite3")
    bridge = ArtifactSimulationBridge(artifact_store=store, sinking_registry=sinks)
    artifact = catalog[0]
    carrier = {
        "id": "UUV-AUTH", "crewId": "crew-alpha", "unitType": "submersible",
        "x": artifact["x"], "y": artifact["y"], "afloat": True,
        "lockedArtifactContainer": {"locked": True, "artifactIds": []},
    }
    store.discover("PELAGOS-01", artifact["id"])
    store.collect("PELAGOS-01", artifact["id"], "UUV-AUTH", carrier)
    sunk = {**carrier, "x": 0.371, "y": 0.824, "afloat": False}
    environment = VigilEnvironment(enabled=True)
    environment.configure_artifact_recovery(
        world_seed="PELAGOS-01",
        bridge=bridge,
        resolve_unit_state=lambda unit_id: sunk if unit_id == "UUV-AUTH" else None,
    )

    event = environment.confirm_unit_sunk(
        event_id="authoritative-sink-01",
        timestamp_ns=900,
        unit_id="UUV-AUTH",
        authoritative_unit_state=sunk,
    )
    assert event.kind == "UNIT_SUNK"
    assert event.payload["x"] == 0.371
    assert event.payload["y"] == 0.824
    recovered = next(item for item in store.inventory("PELAGOS-01") if item["id"] == artifact["id"])
    assert recovered["status"] == "LOST"
    assert recovered["location"] == {"x": 0.371, "y": 0.824}

    with __import__("pytest").raises(ValueError, match="only an authoritative sunk submersible"):
        environment.confirm_unit_sunk(
            event_id="fake-sink-02", timestamp_ns=901, unit_id="UUV-AUTH",
            authoritative_unit_state={**sunk, "afloat": True},
        )
    environment.disable_artifact_recovery()
    store.close()
    sinks.close()


def test_confirm_unit_removed_recovers_carried_artifact_at_authoritative_position(tmp_path):
    from vigil.artifact_simulation_bridge import ArtifactSimulationBridge
    from vigil.historical_artifact_catalog import build_artifact_catalog
    from vigil.historical_artifact_store import HistoricalArtifactStore
    from vigil.sinking_event_registry import SinkingEventRegistry

    catalog = build_artifact_catalog()
    store = HistoricalArtifactStore(catalog, tmp_path / "artifacts.sqlite3")
    sinks = SinkingEventRegistry(tmp_path / "sinks.sqlite3")
    bridge = ArtifactSimulationBridge(artifact_store=store, sinking_registry=sinks)
    artifact = catalog[0]
    carrier = {
        "id": "UUV-REMOVED", "crewId": "crew-alpha", "unitType": "submersible",
        "x": artifact["x"], "y": artifact["y"], "afloat": True,
        "lockedArtifactContainer": {"locked": True, "artifactIds": []},
    }
    store.discover("PELAGOS-01", artifact["id"])
    store.collect("PELAGOS-01", artifact["id"], "UUV-REMOVED", carrier)
    removed = {**carrier, "x": 0.412, "y": 0.733}
    environment = VigilEnvironment(enabled=True)
    environment.configure_artifact_recovery(
        world_seed="PELAGOS-01", bridge=bridge,
        resolve_unit_state=lambda unit_id: removed if unit_id == "UUV-REMOVED" else None,
    )

    event = environment.confirm_unit_removed(
        event_id="decommission-01", timestamp_ns=1000,
        unit_id="UUV-REMOVED", authoritative_unit_state=removed,
    )
    assert event.kind == "UNIT_REMOVED"
    recovered = next(item for item in store.inventory("PELAGOS-01") if item["id"] == artifact["id"])
    assert recovered["status"] == "LOST"
    assert recovered["location"] == {"x": 0.412, "y": 0.733}

    environment.disable_artifact_recovery()
    store.close()
    sinks.close()

def test_recorded_sink_event_can_retry_recovery_after_transient_resolver_failure(tmp_path):
    from vigil.artifact_replay_consumer import ArtifactReplayConsumer
    from vigil.artifact_simulation_bridge import ArtifactSimulationBridge
    from vigil.historical_artifact_catalog import build_artifact_catalog
    from vigil.historical_artifact_store import HistoricalArtifactStore
    from vigil.provenance import EventProvenance
    from vigil.simulation import ReplayEvent, ReplayLog
    from vigil.sinking_event_registry import SinkingEventRegistry
    import pytest

    catalog = build_artifact_catalog()
    store = HistoricalArtifactStore(catalog, tmp_path / "retry-artifacts.sqlite3")
    sinks = SinkingEventRegistry(tmp_path / "retry-sinks.sqlite3")
    artifact = catalog[0]
    carrier = {"id": "UUV-RETRY", "crewId": "crew-alpha", "unitType": "submersible",
               "x": artifact["x"], "y": artifact["y"], "afloat": True,
               "lockedArtifactContainer": {"locked": True, "artifactIds": []}}
    store.discover("PELAGOS-01", artifact["id"])
    store.collect("PELAGOS-01", artifact["id"], "UUV-RETRY", carrier)
    sunk = {**carrier, "x": 0.23, "y": 0.76, "afloat": False}
    state = {"available": False}
    consumer = ArtifactReplayConsumer(
        world_seed="PELAGOS-01",
        bridge=ArtifactSimulationBridge(artifact_store=store, sinking_registry=sinks),
        resolve_unit_state=lambda unit_id: sunk if state["available"] else None,
    )
    log = ReplayLog()
    consumer.attach(log)
    event = ReplayEvent(
        event_id="retry-sink-01", timestamp_ns=1, kind="UNIT_SUNK",
        payload={"status": "CONFIRMED", "unit_id": "UUV-RETRY", "x": 0.23, "y": 0.76},
        provenance=EventProvenance(source_type="simulation", source_ids=("UUV-RETRY",),
                                   timestamp_ns=1, confidence=1.0),
    )
    with pytest.raises(ValueError, match="authoritative sunk-unit state is unavailable"):
        log.append(event)
    assert log.events == (event,)
    state["available"] = True
    result = consumer.reconcile_recorded_events(log)
    assert result == {"processed": 1, "ignored": 0, "recovered": 1, "failures": []}
    item = next(row for row in store.inventory("PELAGOS-01") if row["id"] == artifact["id"])
    assert item["status"] == "LOST"
    assert item["location"] == {"x": 0.23, "y": 0.76}
    store.close()
    sinks.close()