"""Fault-tolerant dynamic work distribution for 314DNest.

AI cores are treated as interchangeable workers by default. Model-specific
specialties are metadata, not permission boundaries. Independent work is
continuously assigned to whichever healthy core becomes available, and failed
work is requeued on another core.
"""

from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
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
    """Dynamically distribute independent work across enabled AI cores."""

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

        worker_ids = cores[: self.max_workers] if self.max_workers else cores
        pending = list(items)
        attempted: dict[str, set[str]] = {item.work_id: set() for item in items}
        completed: dict[str, WorkResult] = {}
        active = {}

        with ThreadPoolExecutor(max_workers=max(1, len(worker_ids))) as executor:
            for model_id in worker_ids:
                self._submit_next(executor, active, pending, attempted, model_id)

            while active:
                done, _ = wait(tuple(active), return_when=FIRST_COMPLETED)
                for future in done:
                    item, model_id = active.pop(future)
                    try:
                        result = future.result()
                    except Exception:
                        remaining = [core for core in cores if core not in attempted[item.work_id]]
                        if remaining:
                            pending.insert(0, item)
                        else:
                            completed[item.work_id] = WorkResult(
                                item.work_id, None, tuple(sorted(attempted[item.work_id]))
                            )
                    else:
                        completed[item.work_id] = WorkResult(item.work_id, result)

                    self._submit_next(executor, active, pending, attempted, model_id)

        return tuple(completed[item.work_id] for item in items)

    def _submit_next(self, executor, active, pending, attempted, model_id: str) -> None:
        if not pending:
            return
        eligible_index = next(
            (index for index, item in enumerate(pending)
             if model_id not in attempted[item.work_id]),
            None,
        )
        if eligible_index is None:
            return
        item = pending.pop(eligible_index)
        attempted[item.work_id].add(model_id)
        future = executor.submit(self._infer_one, item.request, model_id)
        active[future] = (item, model_id)

    def _infer_one(self, request: AIRequest, model_id: str) -> AIResult:
        return self.registry.infer(request, (model_id,))[0]
