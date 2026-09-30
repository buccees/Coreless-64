"""Read-only telemetry contracts for the 314DNest management plane."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping


@dataclass(frozen=True)
class TelemetrySnapshot:
    timestamp: str
    cpu: Mapping[str, float]
    memory: Mapping[str, float]
    storage: Mapping[str, float]
    workloads: Mapping[str, float]
    vms: Mapping[str, float]


class TelemetryProvider:
    """Stores the latest deterministic management telemetry snapshot."""

    def __init__(self) -> None:
        self._snapshot = TelemetrySnapshot(
            timestamp=datetime.now(timezone.utc).isoformat(),
            cpu={},
            memory={},
            storage={},
            workloads={},
            vms={},
        )

    def publish(
        self,
        *,
        cpu: Mapping[str, float] = (),
        memory: Mapping[str, float] = (),
        storage: Mapping[str, float] = (),
        workloads: Mapping[str, float] = (),
        vms: Mapping[str, float] = (),
    ) -> TelemetrySnapshot:
        self._snapshot = TelemetrySnapshot(
            timestamp=datetime.now(timezone.utc).isoformat(),
            cpu=dict(cpu),
            memory=dict(memory),
            storage=dict(storage),
            workloads=dict(workloads),
            vms=dict(vms),
        )
        return self._snapshot

    def snapshot(self) -> TelemetrySnapshot:
        return self._snapshot
