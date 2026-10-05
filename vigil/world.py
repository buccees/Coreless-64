"""Authoritative VIGIL world model and deterministic history."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Mapping
from .model import EntityType, Provenance, Uncertainty, WorldEntity


@dataclass(frozen=True)
class WorldModelEvent:
    event_id: str
    timestamp_ns: int
    entity_id: str
    kind: str
    previous: WorldEntity | None
    current: WorldEntity | None


def _entity_record(entity: WorldEntity | None) -> object:
    if entity is None:
        return None
    return {
        "entity_id": entity.entity_id,
        "entity_type": entity.entity_type.value,
        "label": entity.label,
        "position": None if entity.position is None else list(entity.position),
        "track_id": entity.track_id,
        "confidence": entity.confidence,
        "uncertainty": {
            "position_m": entity.uncertainty.position_m,
            "time_ns": entity.uncertainty.time_ns,
            "classification": entity.uncertainty.classification,
        },
        "provenance": [
            {
                "source_id": item.source_id,
                "source_type": item.source_type,
                "created_ns": item.created_ns,
                "metadata": dict(item.metadata),
            }
            for item in entity.provenance
        ],
        "first_seen_ns": entity.first_seen_ns,
        "last_seen_ns": entity.last_seen_ns,
        "valid": entity.valid,
        "fresh": entity.fresh,
        "metadata": dict(entity.metadata),
    }


def _entity_from_record(record: object) -> WorldEntity | None:
    if record is None:
        return None
    if not isinstance(record, Mapping):
        raise ValueError("world entity record must be a mapping")
    position = record.get("position")
    if position is not None:
        if not isinstance(position, (list, tuple)) or len(position) != 3:
            raise ValueError("world entity position must contain three values")
        position = tuple(float(value) for value in position)
    uncertainty = record.get("uncertainty", {})
    if not isinstance(uncertainty, Mapping):
        raise ValueError("world entity uncertainty must be a mapping")
    provenance = record.get("provenance", ())
    if not isinstance(provenance, (list, tuple)):
        raise ValueError("world entity provenance must be a list")
    return WorldEntity(
        entity_id=str(record["entity_id"]),
        entity_type=EntityType(record["entity_type"]),
        label=record.get("label"),
        position=position,
        track_id=record.get("track_id"),
        confidence=float(record["confidence"]),
        uncertainty=Uncertainty(
            position_m=uncertainty.get("position_m"),
            time_ns=uncertainty.get("time_ns"),
            classification=uncertainty.get("classification"),
        ),
        provenance=tuple(
            Provenance(
                source_id=str(item["source_id"]),
                source_type=str(item["source_type"]),
                created_ns=int(item["created_ns"]),
                metadata=dict(item.get("metadata", {})),
            )
            for item in provenance
        ),
        first_seen_ns=int(record["first_seen_ns"]),
        last_seen_ns=int(record["last_seen_ns"]),
        valid=bool(record.get("valid", True)),
        fresh=bool(record.get("fresh", True)),
        metadata=dict(record.get("metadata", {})),
    )


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

    def persistent_state(self) -> dict[str, object]:
        return {
            "version": 1,
            "entities": [_entity_record(entity) for entity in self.entities()],
            "history": [
                {
                    "event_id": event.event_id,
                    "timestamp_ns": event.timestamp_ns,
                    "entity_id": event.entity_id,
                    "kind": event.kind,
                    "previous": _entity_record(event.previous),
                    "current": _entity_record(event.current),
                }
                for event in self._history
            ],
        }

    def restore_state(self, state: object) -> None:
        if not isinstance(state, Mapping) or state.get("version") != 1:
            raise ValueError("unsupported world model state version")
        entities = state.get("entities", [])
        history = state.get("history", [])
        if not isinstance(entities, list) or not isinstance(history, list):
            raise ValueError("world model entities/history must be lists")
        restored = {_entity_from_record(record).entity_id: _entity_from_record(record) for record in entities}
        events: list[WorldModelEvent] = []
        for record in history:
            if not isinstance(record, Mapping):
                raise ValueError("world model history record must be a mapping")
            events.append(WorldModelEvent(
                str(record["event_id"]),
                int(record["timestamp_ns"]),
                str(record["entity_id"]),
                str(record["kind"]),
                _entity_from_record(record.get("previous")),
                _entity_from_record(record.get("current")),
            ))
        self._entities = restored
        self._history = events
