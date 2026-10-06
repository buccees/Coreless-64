"""Dynamic machine work distribution across conventional and AI resources."""

from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass
from typing import Sequence

from ai.compute_fabric import ComputeResult, ComputeWork
from scheduler import MachineScheduler


@dataclass(frozen=True)
class MachineWorkResult:
    work_id: str
    result: ComputeResult | None
    resource_id: str | None = None
    kind: str | None = None
    error: str | None = None


class MachineWorkDistributor:
    """Split independent machine work across scheduler-managed resources."""

    def __init__(self, scheduler: MachineScheduler, *, max_workers: int | None = None):
        self.scheduler = scheduler
        self.max_workers = max_workers

    def execute(
        self,
        items: Sequence[ComputeWork],
        *,
        preference: str = "balanced",
        allow_fallback: bool = True,
    ) -> tuple[MachineWorkResult, ...]:
        if not items:
            return ()
        if self.max_workers is not None:
            if self.max_workers < 1:
                raise ValueError("max_workers must be positive")
            worker_count = self.max_workers
        else:
            worker_count = max(
                1,
                min(
                    len(items),
                    sum(
                        getattr(self.scheduler._resources[resource_id], "capacity", 1)
                        for resource_id in self.scheduler.resources()
                    ),
                ),
            )
        pending = list(items)
        completed: dict[str, MachineWorkResult] = {}
        active = {}

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            while pending or active:
                while pending and len(active) < worker_count:
                    item = pending.pop(0)
                    future = executor.submit(
                        self.scheduler.execute,
                        item,
                        preference=preference,
                        allow_fallback=allow_fallback,
                    )
                    active[future] = item

                if not active:
                    continue

                done, _ = wait(tuple(active), return_when=FIRST_COMPLETED)
                for future in done:
                    item = active.pop(future)
                    try:
                        result, allocation = future.result()
                    except Exception as exc:
                        completed[item.work_id] = MachineWorkResult(
                            item.work_id, None, error=str(exc)
                        )
                    else:
                        completed[item.work_id] = MachineWorkResult(
                            item.work_id,
                            result,
                            allocation.resource_id,
                            allocation.kind,
                        )

        return tuple(completed[item.work_id] for item in items)
