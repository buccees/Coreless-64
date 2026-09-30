"""Fault-tolerant work distribution for 314DNest.

AI cores are treated as interchangeable workers by default. Model-specific
specialties are metadata, not permission boundaries. Work can be partitioned
across all healthy cores, and the coordinator redistributes failed work.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Sequence

from .interfaces import AIRequest, AIResult
from .registry import AICoreRegistry


@dataclass(frozen=True)
class WorkItem:
    work_id: str
    request: AIRequest


@dataclass(frozen=True)
class WorkResult:
    work_id: str
    result: AIResult | None
    failures: tuple[str, ...] = ()


class WorkDistributor:
    """Distribute independent work items across the currently healthy cores."""

    def __init__(self, registry: AICoreRegistry, *, max_workers: int | None = None) -> None:
        self.registry = registry
        self.max_workers = max_workers

    def execute(self, items: Sequence[WorkItem]) -> tuple[WorkResult, ...]:
        cores = self.registry.enabled_cores()
        if not items:
            return ()
        if not cores:
            return tuple(
                WorkResult(item.work_id, None, ("no enabled AI cores",))
                for item in items
            )

        # Each item is initially assigned to a worker. If that worker fails,
        # the item is retried by another enabled worker. A core can therefore
        # absorb work normally handled by another model.
        assignments = [
            (item, cores[index % len(cores)])
            for index, item in enumerate(items)
        ]
        pending = list(assignments)
        completed: dict[str, WorkResult] = {}
        attempted: dict[str, set[str]] = {item.work_id: set() for item in items}

        workers = self.max_workers or max(1, len(cores))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            while pending:
                futures = {}
                for item, model_id in pending:
                    attempted[item.work_id].add(model_id)
                    futures[
                        executor.submit(
                            self.registry.infer, item.request, (model_id,)
                        )
                    ] = (item, model_id)
                pending = []

                for future in as_completed(futures):
                    item, model_id = futures[future]
                    try:
                        result = future.result()[0]
                    except Exception:
                        remaining = [
                            core
                            for core in cores
                            if core not in attempted[item.work_id]
                        ]
                        if remaining:
                            pending.append((item, remaining[0]))
                        else:
                            completed[item.work_id] = WorkResult(
                                item.work_id,
                                None,
                                tuple(sorted(attempted[item.work_id])),
                            )
                    else:
                        completed[item.work_id] = WorkResult(item.work_id, result)

        return tuple(completed[item.work_id] for item in items)
