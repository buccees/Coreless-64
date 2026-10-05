"""Authoritative VIGIL world model and deterministic history."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
from .model import WorldEntity


@dataclass(frozen=True)
class WorldModelEvent:
    event_id: str
    timestamp_ns: int
    entity_id: str
    kind: str
    previous: WorldEntity | None
    current: WorldEntity | None


class WorldModel:
    """Owns current VIGIL spatial belief; derived layers cannot mutate it."""

    def __init__(self) -> None:
        self._entities: dict[str, WorldEntity] = {}
        self._history: list[WorldModelEvent] = []

    def get(self, entity_id: str) -> WorldEntity | None:
        return self._entities.get(entity_id)

    def entities(self) -> tuple[WorldEntity, ...]:
        return tuple(self._entities[key] for key in sorted(self._entities))

    def history(self) -> tuple[WorldModelEvent, ...]:
        return tuple(self._history)

    def upsert(self, entity: WorldEntity, *, event_id: str, timestamp_ns: int) -> WorldModelEvent:
        previous = self._entities.get(entity.entity_id)
        self._entities[entity.entity_id] = entity
        kind = "created" if previous is None else "updated"
        event = WorldModelEvent(event_id, timestamp_ns, entity.entity_id, kind, previous, entity)
        self._history.append(event)
        return event

    def remove(self, entity_id: str, *, event_id: str, timestamp_ns: int) -> WorldModelEvent | None:
        previous = self._entities.pop(entity_id, None)
        if previous is None:
            return None
        event = WorldModelEvent(event_id, timestamp_ns, entity_id, "removed", previous, None)
        self._history.append(event)
        return event

    def replace_many(self, entities: Iterable[WorldEntity], *, timestamp_ns: int) -> tuple[WorldModelEvent, ...]:
        events = []
        for entity in sorted(entities, key=lambda value: value.entity_id):
            events.append(self.upsert(entity, event_id=f"world-{entity.entity_id}-{timestamp_ns}", timestamp_ns=timestamp_ns))
        return tuple(events)
