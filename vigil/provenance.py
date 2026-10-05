"""Shared provenance contracts for Coreless-native VIGIL event tracing."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class EventProvenance:
    source_type: str
    source_ids: tuple[str, ...] = ()
    source_sequences: tuple[int, ...] = ()
    timestamp_ns: int = 0
    confidence: float | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.source_type:
            raise ValueError("source_type must not be empty")
        if self.timestamp_ns < 0:
            raise ValueError("timestamp_ns must be non-negative")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
