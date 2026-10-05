"""Device-independent presentation state for VIGIL."""
from __future__ import annotations
from typing import Mapping
from .attention import AttentionItem, AttentionLifecycle
from .priority import PriorityResult


class PresentationState:
    def __init__(self, items: tuple[AttentionItem, ...], timestamp_ns: int):
        self.items = items
        self.timestamp_ns = timestamp_ns


class PresentationManager:
    def present(self, items: tuple[AttentionItem, ...], timestamp_ns: int) -> PresentationState:
        ordered = tuple(sorted(items, key=lambda item: (-item.priority.priority, -item.priority.relevance, item.world_entity_id)))
        self._state = PresentationState(ordered, timestamp_ns)
        return self._state

    def state(self) -> PresentationState | None:
        return getattr(self, "_state", None)

    def persistent_state(self) -> dict[str, object]:
        state = self.state()
        return {
            "version": 1,
            "state": None if state is None else {
                "timestamp_ns": state.timestamp_ns,
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
                    for item in state.items
                ],
            },
        }

    def restore_state(self, state: object) -> None:
        if not isinstance(state, Mapping) or state.get("version") != 1:
            raise ValueError("unsupported presentation state version")
        record = state.get("state")
        if record is None:
            self._state = None
            return
        if not isinstance(record, Mapping):
            raise ValueError("presentation state must be a mapping")
        restored = []
        for item in record.get("items", []):
            if not isinstance(item, Mapping) or not isinstance(item.get("priority"), Mapping):
                raise ValueError("presentation item is malformed")
            priority = item["priority"]
            result = PriorityResult(
                world_entity_id=str(priority["world_entity_id"]),
                relevance=float(priority["relevance"]),
                priority=float(priority["priority"]),
                evaluation_time_ns=int(priority["evaluation_time_ns"]),
                contributing_factors=tuple(str(value) for value in priority.get("contributing_factors", ())),
                unavailable_factors=tuple(str(value) for value in priority.get("unavailable_factors", ())),
            )
            restored.append(
                AttentionItem(
                    world_entity_id=str(item["world_entity_id"]),
                    priority=result,
                    lifecycle=AttentionLifecycle(item["lifecycle"]),
                )
            )
        self._state = PresentationState(tuple(restored), int(record["timestamp_ns"]))
