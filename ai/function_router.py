"""Capability/function-based routing for registered Coreless AI models.

The router does not infer model strengths from model names. Deployments declare
the functions each model has been evaluated and approved to serve; assignment
is rejected unless that capability declaration exists.
"""
from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from .registry import AICoreRegistry


class FunctionalModelRouter:
    """Persist model capability declarations and function-to-model assignments."""

    STATE_VERSION = 1
    STORAGE_KEY = "ai/function-routing"

    def __init__(self, registry: AICoreRegistry) -> None:
        self.registry = registry
        self._capabilities: dict[str, list[str]] = {}
        self._assignments: dict[str, list[str]] = {}

    def declare_capabilities(self, model_id: str, functions: Sequence[str]) -> None:
        self.registry.descriptor(model_id)
        normalized = list(dict.fromkeys(self._validate_function(item) for item in functions))
        if not normalized:
            raise ValueError("a model must declare at least one supported function")
        # Do not leave assignments behind if a capability is withdrawn.
        self._capabilities[model_id] = normalized
        for function in tuple(self._assignments):
            if model_id in self._assignments[function] and function not in normalized:
                self._assignments[function].remove(model_id)
                if not self._assignments[function]:
                    del self._assignments[function]

    def assign(self, function: str, model_id: str) -> None:
        function = self._validate_function(function)
        self.registry.descriptor(model_id)
        if function not in self._capabilities.get(model_id, ()):
            raise ValueError(
                f"model {model_id!r} has no declared capability for function {function!r}"
            )
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

    def capabilities(self) -> dict[str, tuple[str, ...]]:
        return {model_id: tuple(items) for model_id, items in sorted(self._capabilities.items())}

    def to_state(self) -> dict[str, object]:
        return {
            "version": self.STATE_VERSION,
            "capabilities": [
                {"model_id": model_id, "functions": list(functions)}
                for model_id, functions in sorted(self._capabilities.items())
            ],
            "assignments": [
                {"function": function, "model_ids": list(model_ids)}
                for function, model_ids in sorted(self._assignments.items())
            ],
        }

    def restore_state(self, state: Mapping[str, object]) -> None:
        if not isinstance(state, Mapping) or state.get("version") != self.STATE_VERSION:
            raise ValueError("unsupported AI function-routing state version")
        capability_entries = state.get("capabilities")
        entries = state.get("assignments")
        if not isinstance(capability_entries, list) or not isinstance(entries, list):
            raise ValueError("AI function-routing state has invalid capabilities or assignments")
        restored_capabilities: dict[str, list[str]] = {}
        for entry in capability_entries:
            if not isinstance(entry, Mapping):
                raise ValueError("AI model-capability entry must be an object")
            model_id = entry.get("model_id")
            functions = entry.get("functions")
            if not isinstance(model_id, str) or model_id in restored_capabilities:
                raise ValueError("AI model-capability entry has invalid or duplicate model ID")
            self.registry.descriptor(model_id)
            if not isinstance(functions, list) or not functions:
                raise ValueError("AI model-capability entry must declare functions")
            normalized = [self._validate_function(item) for item in functions]
            if len(set(normalized)) != len(normalized):
                raise ValueError("AI model-capability entry has duplicate functions")
            restored_capabilities[model_id] = normalized

        restored_assignments: dict[str, list[str]] = {}
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
                if function not in restored_capabilities.get(model_id, ()):
                    raise ValueError(
                        f"model {model_id!r} is assigned to undeclared function {function!r}"
                    )
                seen.add(model_id)
            if function in restored_assignments:
                raise ValueError(f"duplicate AI function-routing entry: {function}")
            restored_assignments[function] = list(model_ids)
        self._capabilities = restored_capabilities
        self._assignments = restored_assignments

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
