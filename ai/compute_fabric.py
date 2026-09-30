"""AI computational resource layer for the Coreless machine.

AI cores are computational resources inside Coreless, not privileged owners of
the machine. Work is submitted through this boundary and remains subject to
the normal deterministic policy/management layers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .interfaces import AIRequest, AIResult
from .registry import AICoreRegistry


@dataclass(frozen=True)
class ComputeWork:
    work_id: str
    operation: str
    request: AIRequest


@dataclass(frozen=True)
class ComputeResult:
    work_id: str
    operation: str
    model_id: str
    result: AIResult


class AIComputeResource(Protocol):
    """Minimum contract for an AI-backed Coreless compute resource."""

    @property
    def model_id(self) -> str:
        ...

    def compute(self, work: ComputeWork) -> ComputeResult:
        ...


class RegisteredAICoreResource:
    """Expose one registered AI core as a Coreless computational resource."""

    def __init__(self, registry: AICoreRegistry, model_id: str) -> None:
        self.registry = registry
        self._model_id = model_id

    @property
    def model_id(self) -> str:
        return self._model_id

    def compute(self, work: ComputeWork) -> ComputeResult:
        result = self.registry.infer(work.request, (self.model_id,))[0]
        return ComputeResult(work.work_id, work.operation, self.model_id, result)


class AIComputeFabric:
    """Register AI compute resources and dispatch machine work to them."""

    def __init__(self) -> None:
        self._resources: dict[str, AIComputeResource] = {}

    def register(self, resource: AIComputeResource) -> None:
        if resource.model_id in self._resources:
            raise ValueError(f"AI compute resource already registered: {resource.model_id}")
        self._resources[resource.model_id] = resource

    def unregister(self, model_id: str) -> None:
        self._resources.pop(model_id)

    def resources(self) -> tuple[str, ...]:
        return tuple(sorted(self._resources))

    def compute(self, work: ComputeWork, model_id: str) -> ComputeResult:
        try:
            resource = self._resources[model_id]
        except KeyError as exc:
            raise KeyError(f"unknown AI compute resource: {model_id}") from exc
        return resource.compute(work)
