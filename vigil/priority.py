"""Explainable deterministic relevance and priority."""
from __future__ import annotations
from dataclasses import dataclass, field
from .model import WorldEntity
from .fusion import distance


@dataclass(frozen=True)
class PriorityContext:
    timestamp_ns: int
    reference_position: tuple[float, float, float] | None = None
    task: str | None = None
    selected_entity_id: str | None = None


@dataclass(frozen=True)
class PriorityResult:
    world_entity_id: str
    relevance: float
    priority: float
    evaluation_time_ns: int
    contributing_factors: tuple[str, ...] = ()
    unavailable_factors: tuple[str, ...] = ()


class RelevancePriorityEngine:
    def evaluate(self, entity: WorldEntity, context: PriorityContext) -> PriorityResult:
        factors: list[str] = []
        unavailable: list[str] = []
        relevance = 0.0
        priority = 0.0

        if context.reference_position is not None and entity.position is not None:
            proximity = 1.0 / (1.0 + distance(context.reference_position, entity.position))
            relevance += proximity
            priority += proximity
            factors.append("proximity")
        else:
            unavailable.append("proximity")

        if context.selected_entity_id == entity.entity_id:
            relevance += 1.0
            priority += 1.0
            factors.append("selected")
        elif context.selected_entity_id is None:
            unavailable.append("selection")

        if context.task and entity.label and context.task.lower() in entity.label.lower():
            relevance += 1.0
            priority += 1.0
            factors.append("task")
        elif context.task is None:
            unavailable.append("task")

        return PriorityResult(
            world_entity_id=entity.entity_id,
            relevance=relevance,
            priority=priority,
            evaluation_time_ns=context.timestamp_ns,
            contributing_factors=tuple(factors),
            unavailable_factors=tuple(unavailable),
        )

    def order(self, results: tuple[PriorityResult, ...]) -> tuple[PriorityResult, ...]:
        return tuple(sorted(results, key=lambda item: (-item.priority, -item.relevance, item.world_entity_id)))
