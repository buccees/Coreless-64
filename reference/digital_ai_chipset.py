"""Programmable digital AI chipset controller for the Coreless virtual board.

This is software control logic, not a physical accelerator or a second AI runtime.
All inference still executes through the existing Coreless scheduler and AI fabric.
"""
from __future__ import annotations

from typing import Any

from ai.compute_fabric import ComputeWork


class DigitalAIChipset:
    """Digital control/status endpoint directly coupled to the machine scheduler."""

    INTERFACE_VERSION = 1
    CHIPSET_ID = "coreless.digital-ai-chipset"
    # The operations advertised by the existing AI scheduler adapter.
    SUPPORTED_OPERATIONS = frozenset({
        "ai.infer", "tensor.matmul", "tensor.linear", "tensor.softmax",
        "transformer.attention", "transformer.block",
    })

    def __init__(self, machine: Any) -> None:
        self.machine = machine
        self.enabled = True
        self.busy = False
        self.fault: str | None = None
        self.completed_work = 0
        self.failed_work = 0
        self.last_work_id: str | None = None
        self.last_resource_id: str | None = None
        self._publish()

    @property
    def ready(self) -> bool:
        return self.enabled and self.fault is None and bool(self.machine.ai_fabric.resources())

    def enable(self) -> None:
        self.enabled = True
        self._publish()

    def disable(self) -> None:
        if self.busy:
            raise RuntimeError("cannot disable digital AI chipset while work is active")
        self.enabled = False
        self._publish()

    def reset(self) -> None:
        """Reset controller state without clearing AI sessions or machine storage."""
        if self.busy:
            raise RuntimeError("cannot reset digital AI chipset while work is active")
        self.fault = None
        self.last_work_id = None
        self.last_resource_id = None
        self._publish()

    def clear_fault(self) -> None:
        self.fault = None
        self._publish()

    def dispatch(self, work: ComputeWork, *, model_id: str | None = None):
        """Dispatch supported AI work via the existing scheduler, with no fallback."""
        if not self.enabled:
            raise RuntimeError("digital AI chipset is disabled")
        if self.fault is not None:
            raise RuntimeError(f"digital AI chipset is faulted: {self.fault}")
        if self.busy:
            raise RuntimeError("digital AI chipset is busy")
        if work.operation not in self.SUPPORTED_OPERATIONS:
            raise ValueError(f"unsupported digital AI chipset operation: {work.operation}")
        selected_model = model_id or work.model_id
        if not selected_model:
            raise ValueError("AI work must identify a registered model")
        if selected_model not in self.machine.ai_fabric.resources():
            raise RuntimeError(f"AI model is not registered with the chipset: {selected_model}")
        if work.model_id != selected_model:
            work = ComputeWork(work.work_id, work.operation, work.request, selected_model)
        self.busy = True
        self.last_work_id = work.work_id
        self._publish()
        try:
            result, allocation = self.machine.schedule_compute(
                work, preference="ai_only", allow_fallback=False
            )
            if allocation.kind != "ai" or allocation.resource_id != f"ai:{selected_model}":
                raise RuntimeError("AI scheduler returned unexpected resource provenance")
            self.completed_work += 1
            self.last_resource_id = allocation.resource_id
            return result
        except Exception as exc:
            self.failed_work += 1
            self.fault = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            self.busy = False
            self._publish()

    def snapshot(self) -> dict[str, object]:
        return {
            "chipset_id": self.CHIPSET_ID,
            "interface_version": self.INTERFACE_VERSION,
            "enabled": self.enabled,
            "ready": self.ready,
            "busy": self.busy,
            "fault": self.fault,
            "completed_work": self.completed_work,
            "failed_work": self.failed_work,
            "last_work_id": self.last_work_id,
            "last_resource_id": self.last_resource_id,
            "registered_models": self.machine.ai_fabric.resources(),
            "signals": self.machine.motherboard.ai_chipset_status(),
        }

    def _publish(self) -> None:
        self.machine.motherboard.set_ai_chipset_status(
            ready=self.ready, busy=self.busy, fault=self.fault is not None,
            enabled=self.enabled,
        )
