"""Coreless machine scheduler with conventional and AI compute resources.

AI is a peer computational resource: the scheduler may use it to augment,
replace, or fall back for conventional work without removing conventional
resources.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ai.compute_fabric import AIComputeFabric, ComputeResult, ComputeWork


class MachineComputeResource(Protocol):
    resource_id: str
    kind: str
    capabilities: frozenset[str]

    def execute(self, work: ComputeWork) -> ComputeResult: ...


@dataclass(frozen=True)
class Allocation:
    work_id: str
    resource_id: str
    kind: str
    fallback_used: bool = False


class MachineScheduler:
    """Deterministically allocate compute work across machine resources."""

    def __init__(self) -> None:
        self._resources: dict[str, MachineComputeResource] = {}

    def register(self, resource: MachineComputeResource) -> None:
        if resource.resource_id in self._resources:
            raise ValueError(f"compute resource already registered: {resource.resource_id}")
        self._resources[resource.resource_id] = resource

    def resources(self) -> tuple[str, ...]:
        return tuple(sorted(self._resources))

    def allocate(
        self,
        work: ComputeWork,
        *,
        preference: str = "balanced",
        allow_fallback: bool = True,
    ) -> tuple[MachineComputeResource, bool]:
        if preference not in {"balanced", "conventional", "ai", "ai_only", "conventional_only"}:
            raise ValueError("invalid compute preference")

        conventional = [
            r for r in self._resources.values()
            if r.kind == "conventional" and self._supports(r, work)
        ]
        ai = [
            r for r in self._resources.values()
            if r.kind == "ai" and self._supports(r, work)
        ]

        if preference in {"ai", "ai_only"}:
            ordered = [(r, False) for r in ai]
            if preference == "ai" and allow_fallback:
                ordered += [(r, True) for r in conventional]
        elif preference in {"conventional", "conventional_only"}:
            ordered = [(r, False) for r in conventional]
            if preference == "conventional" and allow_fallback:
                ordered += [(r, True) for r in ai]
        else:
            # Balanced mode preserves the conventional path first and uses AI
            # as an acceleration/fallback resource.
            ordered = [(r, False) for r in conventional] + [(r, True) for r in ai]

        if not ordered:
            raise RuntimeError(f"no compute resource supports operation: {work.operation}")
        return ordered[0]

    def execute(
        self,
        work: ComputeWork,
        *,
        preference: str = "balanced",
        allow_fallback: bool = True,
    ) -> tuple[ComputeResult, Allocation]:
        resource, fallback = self.allocate(
            work, preference=preference, allow_fallback=allow_fallback
        )
        try:
            result = resource.execute(work)
        except Exception:
            if not allow_fallback:
                raise
            alternatives = [
                r for r in self._resources.values()
                if r.resource_id != resource.resource_id
                and r.kind != resource.kind
                and self._supports(r, work)
            ]
            if not alternatives:
                raise
            resource = alternatives[0]
            result = resource.execute(work)
            fallback = True

        return result, Allocation(
            work.work_id, resource.resource_id, resource.kind, fallback
        )

    @staticmethod
    def _supports(resource: MachineComputeResource, work: ComputeWork) -> bool:
        return not resource.capabilities or work.operation in resource.capabilities


class AIComputeSchedulerResource:
    """Adapter exposing one AI fabric core to the machine scheduler."""

    kind = "ai"

    def __init__(self, fabric: AIComputeFabric, model_id: str, capabilities=()):
        self.fabric = fabric
        self.resource_id = f"ai:{model_id}"
        self.model_id = model_id
        self.capabilities = frozenset(capabilities)

    def execute(self, work: ComputeWork) -> ComputeResult:
        return self.fabric.compute(work, self.model_id)


class ConventionalComputeResource:
    """Adapter for a deterministic Coreless compute callback."""

    kind = "conventional"

    def __init__(self, resource_id, execute, capabilities=()):
        self.resource_id = resource_id
        self._execute = execute
        self.capabilities = frozenset(capabilities)

    def execute(self, work: ComputeWork) -> ComputeResult:
        return self._execute(work)
