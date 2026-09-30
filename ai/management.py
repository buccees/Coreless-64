"""Integrated 314DNest management plane for Coreless resources."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .audit import AuditLog
from .interfaces import AIProposal
from .resource_control import CorelessResourceController
from .telemetry import TelemetryProvider


@dataclass(frozen=True)
class ManagementResult:
    allowed: bool
    result: Mapping[str, Any] | None
    audit_event_id: str


class ManagementPlane:
    """Combines telemetry, policy-bound resource control, and audit."""

    def __init__(
        self,
        controller: CorelessResourceController,
        *,
        telemetry: TelemetryProvider | None = None,
        audit: AuditLog | None = None,
    ) -> None:
        self.controller = controller
        self.telemetry = telemetry or TelemetryProvider()
        self.audit = audit or AuditLog()
        self._counter = 0

    def snapshot(self):
        return self.telemetry.snapshot()

    def execute(self, proposal: AIProposal, *, actor: str = "314DNest") -> ManagementResult:
        self._counter += 1
        event_id = f"management:{self._counter}"
        try:
            result = self.controller.execute(proposal)
        except Exception as exc:
            self.audit.record(
                event_id,
                event="resource_action",
                actor=actor,
                operation=proposal.operation,
                outcome="denied_or_failed",
                details={"proposal_id": proposal.proposal_id, "error": type(exc).__name__},
            )
            raise
        self.audit.record(
            event_id,
            event="resource_action",
            actor=actor,
            operation=proposal.operation,
            outcome="executed",
            details={"proposal_id": proposal.proposal_id},
        )
        return ManagementResult(True, result, event_id)
