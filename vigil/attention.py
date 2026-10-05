"""Deterministic attention/presentation state."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
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
