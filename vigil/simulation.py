"""Hardware-independent VIGIL simulation/replay foundation."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from .model import Observation
from .provenance import EventProvenance


@dataclass(frozen=True)
class SimulationFrame:
    timestamp_ns: int
    observations: tuple[Observation, ...]


class ReplaySource:
    def __init__(self, frames: tuple[SimulationFrame, ...] = ()) -> None:
        self._frames = tuple(sorted(frames, key=lambda frame: frame.timestamp_ns))
        self._index = 0

    def reset(self) -> None:
        self._index = 0

    def next(self) -> SimulationFrame | None:
        if self._index >= len(self._frames):
            return None
        frame = self._frames[self._index]
        self._index += 1
        return frame


@dataclass(frozen=True)
class ReplayEvent:
    event_id: str
    timestamp_ns: int
    kind: str
    payload: object
    provenance: EventProvenance | None = None

    def chain_signature(self) -> tuple[object, ...]:
        provenance = self.provenance
        return (
            self.event_id,
            self.timestamp_ns,
            self.kind,
            None if provenance is None else (
                provenance.source_type,
                provenance.source_ids,
                provenance.source_sequences,
                provenance.timestamp_ns,
                provenance.confidence,
            ),
        )


@dataclass(frozen=True)
class ReplayValidation:
    valid: bool
    event_count: int
    mismatches: tuple[str, ...] = ()


class ReplayLog:
    """Deterministic append-only VIGIL event log for audit and replay."""

    def __init__(self, events: tuple[ReplayEvent, ...] = ()) -> None:
        self._events = tuple(events)
        self._last_timestamp = self._events[-1].timestamp_ns if self._events else -1

    @property
    def events(self) -> tuple[ReplayEvent, ...]:
        return self._events

    def append(self, event: ReplayEvent) -> None:
        if event.timestamp_ns < self._last_timestamp:
            raise ValueError("replay events must be monotonic by timestamp")
        if any(existing.event_id == event.event_id for existing in self._events):
            raise ValueError("replay event_id must be unique")
        self._events = self._events + (event,)
        self._last_timestamp = event.timestamp_ns

    def reset(self) -> None:
        self._last_timestamp = self._events[-1].timestamp_ns if self._events else -1

    def replay(self) -> tuple[ReplayEvent, ...]:
        return self._events

    def replay_into(self, consumer) -> tuple[object, ...]:
        results = []
        for event in self._events:
            result = consumer(event)
            if result is not None:
                results.append(result)
        return tuple(results)

    def chain_digest(self) -> str:
        """Return a deterministic digest of the complete event/provenance chain."""
        digest = hashlib.sha256()
        for event in self._events:
            digest.update(repr(event.chain_signature()).encode("utf-8"))
        return digest.hexdigest()

    def integrity_record(self) -> dict[str, object]:
        """Return a persistent integrity record for the current chain."""
        return {
            "version": 1,
            "algorithm": "sha256",
            "event_count": len(self._events),
            "chain_digest": self.chain_digest(),
        }

    def verify_integrity(self, record) -> ReplayValidation:
        """Verify a persisted integrity record before replay."""
        expected_count = int(record.get("event_count", -1))
        expected_digest = str(record.get("chain_digest", ""))
        mismatches = []
        if expected_count != len(self._events):
            mismatches.append(
                f"integrity.event_count: expected {expected_count}, got {len(self._events)}"
            )
        if expected_digest != self.chain_digest():
            mismatches.append("integrity.chain_digest: replay chain integrity mismatch")
        return ReplayValidation(
            valid=not mismatches,
            event_count=len(self._events),
            mismatches=tuple(mismatches),
        )

    def validate_replay(
        self,
        replayed_events: tuple[ReplayEvent, ...],
    ) -> ReplayValidation:
        """Compare a replayed event chain against the original deterministically."""
        expected = self._events
        actual = tuple(replayed_events)
        mismatches: list[str] = []

        if len(expected) != len(actual):
            mismatches.append(
                f"event_count: expected {len(expected)}, got {len(actual)}"
            )

        for index in range(max(len(expected), len(actual))):
            if index >= len(expected):
                mismatches.append(f"event[{index}]: unexpected replay event")
                continue
            if index >= len(actual):
                mismatches.append(f"event[{index}]: missing replay event")
                continue
            if expected[index].chain_signature() != actual[index].chain_signature():
                mismatches.append(
                    f"event[{index}] {expected[index].event_id}: "
                    "event/provenance chain mismatch"
                )

        return ReplayValidation(
            valid=not mismatches,
            event_count=len(actual),
            mismatches=tuple(mismatches),
        )
