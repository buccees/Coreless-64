"""Coreless machine scheduler with conventional and AI compute resources."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
import threading

from ai.compute_fabric import AIComputeFabric, ComputeResult, ComputeWork
from ai.telemetry import TelemetryProvider


class MachineComputeResource(Protocol):
    resource_id: str
    kind: str
    capabilities: frozenset[str]
    capacity: int

    def execute(self, work: ComputeWork) -> ComputeResult: ...


@dataclass(frozen=True)
class Allocation:
    work_id: str
    resource_id: str
    kind: str
    fallback_used: bool = False


class MachineScheduler:
    """Deterministically allocate work using capability, capacity, and load."""

    def __init__(self, telemetry: TelemetryProvider | None = None) -> None:
        self.telemetry = telemetry
        self._resources: dict[str, MachineComputeResource] = {}
        self._load: dict[str, int] = {}
        self._lock = threading.Lock()

    def register(self, resource: MachineComputeResource) -> None:
        if resource.resource_id in self._resources:
            raise ValueError(f"compute resource already registered: {resource.resource_id}")
        if resource.capacity < 1:
            raise ValueError("compute resource capacity must be positive")
        self._resources[resource.resource_id] = resource
        self._load[resource.resource_id] = 0

    def resources(self) -> tuple[str, ...]:
        return tuple(sorted(self._resources))

    def load(self, resource_id: str) -> int:
        return self._load[resource_id]

    def allocate(self, work: ComputeWork, *, preference="balanced",
                 allow_fallback=True) -> tuple[MachineComputeResource, bool]:
        if preference not in {"balanced", "conventional", "ai", "ai_only", "conventional_only"}:
            raise ValueError("invalid compute preference")

        conventional = [r for r in self._resources.values()
                        if r.kind == "conventional" and self._supports(r, work)]
        ai = [r for r in self._resources.values()
              if r.kind == "ai" and self._supports(r, work)]

        if preference in {"ai", "ai_only"}:
            ordered = [(r, False) for r in ai]
            if preference == "ai" and allow_fallback:
                ordered += [(r, True) for r in conventional]
        elif preference in {"conventional", "conventional_only"}:
            ordered = [(r, False) for r in conventional]
            if preference == "conventional" and allow_fallback:
                ordered += [(r, True) for r in ai]
        else:
            ordered = [(r, False) for r in conventional] + [(r, True) for r in ai]

        available = [(r, fb) for r, fb in ordered if self._load[r.resource_id] < r.capacity]
        if not available:
            raise RuntimeError(f"all compute resources are at capacity for operation: {work.operation}")

        snapshot = self.telemetry.snapshot() if self.telemetry is not None else None

        def score(item):
            resource = item[0]
            load_ratio = self._load[resource.resource_id] / resource.capacity
            external = 0.0
            if snapshot is not None:
                source = snapshot.cpu if resource.kind == "conventional" else snapshot.workloads
                external = max(0.0, float(source.get(resource.resource_id, 0.0)))
            return (load_ratio + external, load_ratio, external, resource.resource_id)

        return min(available, key=score)

    def execute(self, work: ComputeWork, *, preference="balanced",
                allow_fallback=True) -> tuple[ComputeResult, Allocation]:
        with self._lock:
            resource, fallback = self.allocate(work, preference=preference, allow_fallback=allow_fallback)
            primary_id = resource.resource_id
            self._load[primary_id] += 1
        try:
            try:
                result = resource.execute(work)
            except Exception:
                if not allow_fallback:
                    raise
                with self._lock:
                    alternatives = sorted(
                        (r for r in self._resources.values()
                         if r.resource_id != primary_id
                         and r.kind != resource.kind
                         and self._supports(r, work)
                         and self._load[r.resource_id] < r.capacity),
                        key=lambda r: (
                            self._load[r.resource_id] / r.capacity,
                            self._load[r.resource_id],
                            r.resource_id,
                        ),
                    )
                    if not alternatives:
                        raise
                    fallback_resource = alternatives[0]
                    self._load[fallback_resource.resource_id] += 1
                try:
                    result = fallback_resource.execute(work)
                finally:
                    with self._lock:
                        self._load[fallback_resource.resource_id] -= 1
                resource = fallback_resource
                fallback = True
            return result, Allocation(
                work.work_id, resource.resource_id, resource.kind, fallback
            )
        finally:
            with self._lock:
                self._load[primary_id] -= 1

    @staticmethod
    def _supports(resource, work) -> bool:
        if resource.capabilities and work.operation not in resource.capabilities:
            return False
        if work.model_id is not None and resource.kind == "ai":
            return getattr(resource, "model_id", None) == work.model_id
        return True


class AIComputeSchedulerResource:
    kind = "ai"

    def __init__(self, fabric: AIComputeFabric, model_id: str, capabilities=(), capacity=1):
        self.fabric = fabric
        self.resource_id = f"ai:{model_id}"
        self.model_id = model_id
        self.capabilities = frozenset(capabilities)
        self.capacity = capacity

    def execute(self, work: ComputeWork) -> ComputeResult:
        return self.fabric.compute(work, self.model_id)


class ConventionalComputeResource:
    kind = "conventional"

    def __init__(self, resource_id, execute, capabilities=(), capacity=1):
        self.resource_id = resource_id
        self._execute = execute
        self.capabilities = frozenset(capabilities)
        self.capacity = capacity

    def execute(self, work: ComputeWork) -> ComputeResult:
        return self._execute(work)
