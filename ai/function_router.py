"""Capability/function-based routing for registered Coreless AI models.

The router does not infer model strengths from model names. Deployments declare
which functions a model has been evaluated and approved to serve; requests are
routed only to enabled models with an explicit assignment.
"""
from __future__ import annotations

import json
from typing import Any, Mapping

from .registry import AICoreRegistry


class FunctionalModelRouter:
    """Persist explicit function-to-model assignments and resolve eligible cores."""

    STATE_VERSION = 1
    STORAGE_KEY = "ai/function-routing"

    def __init__(self, registry: AICoreRegistry) -> None:
        self.registry = registry
        self._assignments: dict[str, list[str]] = {}

    def assign(self, function: str, model_id: str) -> None:
        function = self._validate_function(function)
        self.registry.descriptor(model_id)
        assigned = self._assignments.setdefault(function, [])
        if model_id not in assigned:
            assigned.append(model_id)

    def unassign(self, function: str, model_id: str) -> None:
        function = self._validate_function(function)
        assigned = self._assignments.get(function)
        if assigned is None or model_id not in assigned:
            raise KeyError(f"no model {model_id!r} assigned to function {function!r}")
        assigned.remove(model_id)
        if not assigned:
            del self._assignments[function]

    def models_for(self, function: str) -> tuple[str, ...]:
        function = self._validate_function(function)
        assigned = self._assignments.get(function, ())
        enabled = set(self.registry.enabled_cores())
        selected = tuple(model_id for model_id in assigned if model_id in enabled)
        if not selected:
            raise LookupError(f"no enabled model is assigned to function {function!r}")
        return selected

    def assignments(self) -> dict[str, tuple[str, ...]]:
        return {name: tuple(models) for name, models in sorted(self._assignments.items())}

    def to_state(self) -> dict[str, object]:
        return {
            "version": self.STATE_VERSION,
            "assignments": [
                {"function": function, "model_ids": list(model_ids)}
                for function, model_ids in sorted(self._assignments.items())
            ],
        }

    def restore_state(self, state: Mapping[str, object]) -> None:
        if not isinstance(state, Mapping) or state.get("version") != self.STATE_VERSION:
            raise ValueError("unsupported AI function-routing state version")
        entries = state.get("assignments")
        if not isinstance(entries, list):
            raise ValueError("AI function-routing state has invalid assignments")
        restored: dict[str, list[str]] = {}
        for entry in entries:
            if not isinstance(entry, Mapping):
                raise ValueError("AI function-routing entry must be an object")
            function = self._validate_function(entry.get("function"))
            model_ids = entry.get("model_ids")
            if not isinstance(model_ids, list) or not model_ids:
                raise ValueError("AI function-routing entry must name at least one model")
            seen: set[str] = set()
            for model_id in model_ids:
                if not isinstance(model_id, str) or model_id in seen:
                    raise ValueError("AI function-routing entry has invalid or duplicate model IDs")
                self.registry.descriptor(model_id)
                seen.add(model_id)
            if function in restored:
                raise ValueError(f"duplicate AI function-routing entry: {function}")
            restored[function] = list(model_ids)
        self._assignments = restored

    def save(self, storage: Any) -> None:
        writer = getattr(storage, "put", None) or getattr(storage, "write", None)
        if not callable(writer):
            raise TypeError("storage does not provide a write operation")
        writer(
            self.STORAGE_KEY,
            json.dumps(self.to_state(), sort_keys=True, separators=(",", ":")).encode("utf-8"),
        )

    def load(self, storage: Any) -> None:
        reader = getattr(storage, "get", None) or getattr(storage, "read", None)
        if not callable(reader):
            raise TypeError("storage does not provide a read operation")
        try:
            raw = reader(self.STORAGE_KEY)
        except KeyError:
            raise KeyError("AI function-routing state not found") from None
        if isinstance(raw, str):
            raw = raw.encode("utf-8")
        try:
            state = json.loads(bytes(raw).decode("utf-8"))
        except (TypeError, ValueError, UnicodeDecodeError) as exc:
            raise ValueError("AI function-routing state is corrupt") from exc
        self.restore_state(state)

    @staticmethod
    def _validate_function(function: object) -> str:
        if not isinstance(function, str) or not function.strip():
            raise ValueError("function must be a non-empty string")
        return function.strip()
