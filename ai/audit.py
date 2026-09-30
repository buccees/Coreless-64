"""Deterministic audit records for AI management actions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping


@dataclass(frozen=True)
class AuditRecord:
    event_id: str
    event: str
    actor: str
    operation: str
    outcome: str
    details: Mapping[str, object]
    timestamp: str


class AuditLog:
    def __init__(self) -> None:
        self._records: list[AuditRecord] = []

    def record(
        self,
        event_id: str,
        *,
        event: str,
        actor: str,
        operation: str,
        outcome: str,
        details: Mapping[str, object] = (),
    ) -> AuditRecord:
        if any(record.event_id == event_id for record in self._records):
            raise ValueError("event_id must be unique")
        record = AuditRecord(
            event_id=event_id,
            event=event,
            actor=actor,
            operation=operation,
            outcome=outcome,
            details=dict(details),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._records.append(record)
        return record

    def records(self) -> tuple[AuditRecord, ...]:
        return tuple(self._records)
