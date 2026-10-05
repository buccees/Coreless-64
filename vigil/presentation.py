"""Device-independent presentation state for VIGIL."""
from __future__ import annotations
from dataclasses import dataclass
from .attention import AttentionItem


@dataclass(frozen=True)
class PresentationState:
    items: tuple[AttentionItem, ...]
    timestamp_ns: int


class PresentationManager:
    def present(self, items: tuple[AttentionItem, ...], timestamp_ns: int) -> PresentationState:
        ordered = tuple(sorted(items, key=lambda item: (-item.priority.priority, -item.priority.relevance, item.world_entity_id)))
        return PresentationState(ordered, timestamp_ns)
