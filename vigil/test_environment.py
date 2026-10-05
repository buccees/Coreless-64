from vigil.attention import AttentionLifecycle
from vigil.model import EntityType, Observation, Provenance, WorldEntity
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
        uncertainty=__import__("vigil.model", fromlist=["Uncertainty"]).Uncertainty(),
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
