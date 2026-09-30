"""314DNest multi-core coordinator.

Coordinates multiple registered AI cores, tolerates individual core failures,
and feeds all successful results into the deterministic collaboration layer.
The coordinator does not authorize or execute protected Coreless operations.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Sequence

from .collaboration import DeterministicCollaboration
from .interfaces import AIRequest, AIResult, CollaborationInterface, GroupResult
from .registry import AICoreRegistry


@dataclass(frozen=True)
class CoreFailure:
    model_id: str
    error_type: str
    message: str


@dataclass(frozen=True)
class CoordinationResult:
    group: GroupResult
    results: Sequence[AIResult]
    failures: Sequence[CoreFailure] = ()


class NestCoordinator:
    """Run enabled AI cores concurrently and coordinate their outputs."""

    def __init__(
        self,
        registry: AICoreRegistry,
        collaboration: CollaborationInterface | None = None,
        *,
        max_workers: int | None = None,
    ) -> None:
        self.registry = registry
        self.collaboration = collaboration or DeterministicCollaboration()
        self.max_workers = max_workers

    def coordinate(
        self,
        request: AIRequest,
        model_ids: Sequence[str] | None = None,
    ) -> CoordinationResult:
        selected = (
            tuple(model_ids)
            if model_ids is not None
            else self.registry.enabled_cores()
        )
        results: list[AIResult] = []
        failures: list[CoreFailure] = []

        with ThreadPoolExecutor(
            max_workers=self.max_workers or max(1, len(selected))
        ) as executor:
            futures = {
                executor.submit(self.registry.infer, request, (model_id,)): model_id
                for model_id in selected
            }
            for future in as_completed(futures):
                model_id = futures[future]
                try:
                    results.extend(future.result())
                except Exception as exc:
                    failures.append(
                        CoreFailure(
                            model_id=model_id,
                            error_type=type(exc).__name__,
                            message=str(exc),
                        )
                    )

        # Preserve the caller's model order after concurrent execution.
        order = {model_id: index for index, model_id in enumerate(selected)}
        results.sort(key=lambda result: order.get(result.model_id, len(order)))

        group = self.collaboration.deliberate(request, tuple(results))
        return CoordinationResult(
            group=group,
            results=tuple(results),
            failures=tuple(sorted(failures, key=lambda failure: order.get(failure.model_id, len(order)))),
        )
