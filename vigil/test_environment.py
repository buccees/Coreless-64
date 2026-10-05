from vigil.attention import AttentionLifecycle
from vigil.model import EntityType, Provenance, Uncertainty, WorldEntity
from vigil.priority import PriorityContext
from vigil.runtime import VigilEnvironment


def test_vigil_environment_is_complete_but_optional():
    environment = VigilEnvironment()
    assert not environment.status().enabled
    assert environment.status().world_entities == 0


def test_world_model_and_attention_are_inside_vigil_environment():
    environment = VigilEnvironment(enabled=True)
    entity = WorldEntity(
        entity_id="entity-1",
        entity_type=EntityType.OBJECT,
        label="camera",
        position=(1.0, 0.0, 0.0),
        track_id=None,
        confidence=1.0,
        uncertainty=Uncertainty(),
        provenance=(Provenance("sensor-1", "camera", 1),),
        first_seen_ns=1,
        last_seen_ns=1,
    )
    environment.world.upsert(entity, event_id="event-1", timestamp_ns=1)
    results = environment.priority.order(
        (environment.priority.evaluate(entity, PriorityContext(2, (0.0, 0.0, 0.0))),)
    )
    items = environment.attention.evaluate(results)
    assert items[0].world_entity_id == "entity-1"
    assert items[0].lifecycle == AttentionLifecycle.ACTIVE


def test_vigil_environment_persists_and_restores_runtime_state():
    source = VigilEnvironment(enabled=True)
    entity = WorldEntity(
        entity_id="entity-restore",
        entity_type=EntityType.TARGET,
        label="target",
        position=(2.0, 0.0, 0.0),
        track_id="track-1",
        confidence=0.8,
        uncertainty=Uncertainty(position_m=0.1),
        provenance=(Provenance("sensor-1", "camera", 10),),
        first_seen_ns=10,
        last_seen_ns=20,
    )
    source.world.upsert(entity, event_id="world-1", timestamp_ns=20)
    result = source.priority.evaluate(entity, PriorityContext(20, (0.0, 0.0, 0.0)))
    source.attention.evaluate((result,))
    source.attention.acknowledge("entity-restore")
    source.interaction.remember("remembered context")

    state = source.persistent_state()
    restored = VigilEnvironment(enabled=False)
    restored.restore_state(state)

    assert restored.enabled
    assert restored.world.get("entity-restore") == entity
    assert restored.world.history()[0].event_id == "world-1"
    assert restored.attention.items()[0].lifecycle == AttentionLifecycle.ACKNOWLEDGED
    assert restored.interaction.persistent_state()["context"] == ["remembered context"]
    assert restored.tracking.persistent_state()["tracks"] == []
    assert restored.presentation.persistent_state()["state"] is None


def test_vigil_presentation_state_round_trips():
    environment = VigilEnvironment(enabled=True)
    entity = WorldEntity(
        entity_id="entity-present", entity_type=EntityType.OBJECT, label="object",
        position=(1.0, 0.0, 0.0), track_id=None, confidence=1.0,
        uncertainty=Uncertainty(), provenance=(Provenance("sensor", "camera", 1),),
        first_seen_ns=1, last_seen_ns=1,
    )
    environment.world.upsert(entity, event_id="event-present", timestamp_ns=1)
    result = environment.priority.evaluate(entity, PriorityContext(2, (0.0, 0.0, 0.0)))
    environment.presentation.present(environment.attention.evaluate((result,)), 2)
    state = environment.persistent_state()
    restored = VigilEnvironment(enabled=False)
    restored.restore_state(state)
    assert restored.presentation.state() == environment.presentation.state()


def test_vigil_world_restore_rejects_duplicate_history_ids():
    environment = VigilEnvironment(enabled=True)
    state = environment.world.persistent_state()
    state["history"] = [
        {"event_id": "duplicate", "timestamp_ns": 1, "entity_id": "x", "kind": "created", "previous": None, "current": None},
        {"event_id": "duplicate", "timestamp_ns": 2, "entity_id": "x", "kind": "updated", "previous": None, "current": None},
    ]
    try:
        environment.world.restore_state(state)
    except ValueError as exc:
        assert "duplicate" in str(exc)
    else:
        raise AssertionError("expected duplicate history id rejection")

