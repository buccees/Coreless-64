"""Explicit ownership registry for AI execution paths in modular Coreless hardware.

The registry is deliberately separate from capability-based component load balancing:
a path names exactly one owning component, one function, and one model identity.
It validates bindings against the existing function router rather than registering
or instantiating model runtimes itself.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class ExecutionPath:
    path_id: str
    component_id: str
    function_id: str
    model_id: str
    operation: str = "ai.infer"

    def __post_init__(self) -> None:
        for field_name in ("path_id", "component_id", "function_id", "model_id", "operation"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")

    def to_dict(self) -> dict[str, str]:
        return {
            "path_id": self.path_id,
            "component_id": self.component_id,
            "function_id": self.function_id,
            "model_id": self.model_id,
            "operation": self.operation,
        }


class ExecutionPathRegistry:
    """Persist path ownership and fail closed when a binding is ambiguous."""

    STATE_VERSION = 1
    STORAGE_KEY = "machine/ai-execution-paths"

    def __init__(self) -> None:
        self._paths: dict[str, ExecutionPath] = {}

    def register(self, path: ExecutionPath, *, replace: bool = False) -> None:
        existing = self._paths.get(path.path_id)
        if existing is not None and existing != path and not replace:
            raise ValueError(f"execution path already registered: {path.path_id}")
        for other in self._paths.values():
            if other.path_id != path.path_id and (
                other.component_id == path.component_id
                and other.function_id == path.function_id
            ):
                raise ValueError(
                    "component/function execution path already has an owner: "
                    f"{path.component_id}/{path.function_id}"
                )
        self._paths[path.path_id] = path

    def unregister(self, path_id: str) -> ExecutionPath:
        try:
            return self._paths.pop(path_id)
        except KeyError as exc:
            raise KeyError(f"unknown execution path: {path_id}") from exc

    def get(self, path_id: str) -> ExecutionPath:
        try:
            return self._paths[path_id]
        except KeyError as exc:
            raise LookupError(f"no execution path registered: {path_id}") from exc

    def all(self) -> tuple[ExecutionPath, ...]:
        return tuple(self._paths[key] for key in sorted(self._paths))

    def for_component(self, component_id: str) -> tuple[ExecutionPath, ...]:
        return tuple(path for path in self.all() if path.component_id == component_id)

    def validate_binding(
        self,
        path_id: str,
        *,
        components: Mapping[str, object],
        function_router: object,
    ) -> ExecutionPath:
        """Validate component health/resident model and explicit path assignment."""
        path = self.get(path_id)
        component = components.get(path.component_id)
        if component is None:
            raise LookupError(f"execution path component is unavailable: {path.component_id}")
        if not bool(getattr(component, "healthy", False)):
            raise RuntimeError(f"execution path component is fault-isolated: {path.component_id}")
        descriptor = getattr(component, "descriptor", None)
        resident_model = getattr(descriptor, "ai_model_id", None)
        if resident_model != path.model_id:
            raise ValueError(
                f"execution path model {path.model_id!r} does not match component "
                f"{path.component_id!r} resident model {resident_model!r}"
            )
        models_for = getattr(function_router, "models_for", None)
        if not callable(models_for):
            raise TypeError("function router does not expose models_for")
        assigned = tuple(models_for(path.function_id))
        if path.model_id not in assigned:
            raise ValueError(
                f"execution path {path.path_id!r} model {path.model_id!r} is not "
                f"assigned to function {path.function_id!r}; got {assigned!r}"
            )
        return path


    def execute(
        self,
        path_id: str,
        *,
        components: Mapping[str, object],
        runtime: object,
        machine: object,
        text: str,
        actor: str = "hardware",
        context: Mapping[str, object] | None = None,
    ) -> object:
        """Execute one owned path through the existing machine AI dispatch stack.

        This method does not create/register a model instance. It validates the
        live component and sole router assignment, then asks PersistentAIRuntime
        to dispatch exactly the path's model through the machine scheduler.
        """
        function_router = getattr(runtime, "function_router", None)
        if function_router is None:
            raise TypeError("AI runtime does not expose its function router")
        path = self.validate_binding(
            path_id, components=components, function_router=function_router
        )
        component = components[path.component_id]
        ai_status = getattr(component, "ai_status", None)
        if not callable(ai_status):
            raise TypeError("execution-path component does not expose AI lifecycle status")
        status = ai_status()
        if not status.get("bound") or not status.get("running"):
            raise RuntimeError(
                f"execution-path component AI is not running: {path.component_id}"
            )
        compute = getattr(runtime, "compute", None)
        if not callable(compute):
            raise TypeError("AI runtime does not expose compute")
        results = compute(
            machine,
            text,
            model_id=path.model_id,
            actor=actor,
            context={
                **dict(context or {}),
                "execution_path_id": path.path_id,
                "component_id": path.component_id,
                "function_id": path.function_id,
            },
            operation=path.operation,
        )
        if not isinstance(results, (tuple, list)) or len(results) != 1:
            raise RuntimeError(
                f"execution path {path.path_id!r} expected exactly one result"
            )
        result = results[0]
        if (
            getattr(result, "model_id", None) != path.model_id
            or getattr(getattr(result, "result", None), "model_id", None) != path.model_id
        ):
            raise RuntimeError(
                f"execution path {path.path_id!r} returned mismatched model provenance"
            )
        return result

    def to_state(self) -> dict[str, object]:
        return {
            "version": self.STATE_VERSION,
            "paths": [path.to_dict() for path in self.all()],
        }

    def restore_state(self, state: Mapping[str, object]) -> None:
        if not isinstance(state, Mapping) or state.get("version") != self.STATE_VERSION:
            raise ValueError("unsupported AI execution-path state version")
        entries = state.get("paths")
        if not isinstance(entries, list):
            raise ValueError("AI execution-path state must contain a paths list")
        restored = ExecutionPathRegistry()
        for entry in entries:
            if not isinstance(entry, Mapping):
                raise ValueError("AI execution-path entry must be an object")
            try:
                path = ExecutionPath(
                    path_id=entry["path_id"],
                    component_id=entry["component_id"],
                    function_id=entry["function_id"],
                    model_id=entry["model_id"],
                    operation=entry.get("operation", "ai.infer"),
                )
            except (KeyError, TypeError) as exc:
                raise ValueError("AI execution-path entry is incomplete") from exc
            restored.register(path)
        self._paths = restored._paths

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
            raise KeyError("AI execution-path state not found") from None
        if isinstance(raw, str):
            raw = raw.encode("utf-8")
        try:
            state = json.loads(bytes(raw).decode("utf-8"))
        except (TypeError, ValueError, UnicodeDecodeError) as exc:
            raise ValueError("AI execution-path state is corrupt") from exc
        self.restore_state(state)
