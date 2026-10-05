"""Deterministic attention/presentation state."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Mapping
from .priority import PriorityResult


class AttentionLifecycle(str, Enum):
    NEW = "new"
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    EXPIRED = "expired"
    DISMISSED = "dismissed"


@dataclass(frozen=True)
class AttentionItem:
    world_entity_id: str
    priority: PriorityResult
    lifecycle: AttentionLifecycle = AttentionLifecycle.NEW


class AttentionManager:
    def __init__(self, max_active: int = 8, minimum_priority: float = 0.0) -> None:
        if max_active < 1:
            raise ValueError("max_active must be positive")
        self.max_active = max_active
        self.minimum_priority = minimum_priority
        self._items: dict[str, AttentionItem] = {}

    def evaluate(self, results: tuple[PriorityResult, ...]) -> tuple[AttentionItem, ...]:
        ordered = sorted(results, key=lambda item: (-item.priority, -item.relevance, item.world_entity_id))
        for result in ordered[: self.max_active]:
            if result.priority < self.minimum_priority:
                continue
            previous = self._items.get(result.world_entity_id)
            lifecycle = previous.lifecycle if previous else AttentionLifecycle.ACTIVE
            self._items[result.world_entity_id] = AttentionItem(result.world_entity_id, result, lifecycle)
        return tuple(self._items[key] for key in sorted(self._items))

    def acknowledge(self, entity_id: str) -> None:
        item = self._items[entity_id]
        self._items[entity_id] = AttentionItem(item.world_entity_id, item.priority, AttentionLifecycle.ACKNOWLEDGED)

    def dismiss(self, entity_id: str) -> None:
        item = self._items[entity_id]
        self._items[entity_id] = AttentionItem(item.world_entity_id, item.priority, AttentionLifecycle.DISMISSED)

    def items(self) -> tuple[AttentionItem, ...]:
        return tuple(self._items[key] for key in sorted(self._items))

    def persistent_state(self) -> dict[str, object]:
        return {
            "version": 1,
            "max_active": self.max_active,
            "minimum_priority": self.minimum_priority,
            "items": [
                {
                    "world_entity_id": item.world_entity_id,
                    "lifecycle": item.lifecycle.value,
                    "priority": {
                        "world_entity_id": item.priority.world_entity_id,
                        "relevance": item.priority.relevance,
                        "priority": item.priority.priority,
                        "evaluation_time_ns": item.priority.evaluation_time_ns,
                        "contributing_factors": list(item.priority.contributing_factors),
                        "unavailable_factors": list(item.priority.unavailable_factors),
                    },
                }
                for item in self.items()
            ],
        }

    def restore_state(self, state: object) -> None:
        if not isinstance(state, Mapping) or state.get("version") != 1:
            raise ValueError("unsupported attention state version")
        items = state.get("items", [])
        if not isinstance(items, list):
            raise ValueError("attention items must be a list")
        restored: dict[str, AttentionItem] = {}
        for record in items:
            if not isinstance(record, Mapping):
                raise ValueError("attention item must be a mapping")
            priority = record.get("priority")
            if not isinstance(priority, Mapping):
                raise ValueError("attention priority must be a mapping")
            result = PriorityResult(
                world_entity_id=str(priority["world_entity_id"]),
                relevance=float(priority["relevance"]),
                priority=float(priority["priority"]),
                evaluation_time_ns=int(priority["evaluation_time_ns"]),
                contributing_factors=tuple(str(item) for item in priority.get("contributing_factors", ())),
                unavailable_factors=tuple(str(item) for item in priority.get("unavailable_factors", ())),
            )
            entity_id = str(record["world_entity_id"])
            restored[entity_id] = AttentionItem(entity_id, result, AttentionLifecycle(record["lifecycle"]))
        self.max_active = int(state.get("max_active", self.max_active))
        self.minimum_priority = float(state.get("minimum_priority", self.minimum_priority))
        self._items = restored
