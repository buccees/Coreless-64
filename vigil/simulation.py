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

    def to_record(self) -> dict[str, object]:
        """Serialize the event into a deterministic, JSON-compatible record."""
        provenance = self.provenance
        return {
            "event_id": self.event_id,
            "timestamp_ns": self.timestamp_ns,
            "kind": self.kind,
            "payload": _encode_value(self.payload),
            "provenance": None if provenance is None else {
                "source_type": provenance.source_type,
                "source_ids": list(provenance.source_ids),
                "source_sequences": list(provenance.source_sequences),
                "timestamp_ns": provenance.timestamp_ns,
                "confidence": provenance.confidence,
                "metadata": _encode_value(provenance.metadata),
            },
        }

    @classmethod
    def from_record(cls, record: object) -> "ReplayEvent":
        """Reconstruct an event record without executing arbitrary serialized code."""
        if not isinstance(record, Mapping):
            raise ValueError("replay event record must be a mapping")
        event_id = record.get("event_id")
        timestamp_ns = record.get("timestamp_ns")
        kind = record.get("kind")
        if not isinstance(event_id, str) or not event_id:
            raise ValueError("replay event_id must be a non-empty string")
        if not isinstance(timestamp_ns, int) or isinstance(timestamp_ns, bool) or timestamp_ns < 0:
            raise ValueError("replay timestamp_ns must be a non-negative integer")
        if not isinstance(kind, str) or not kind:
            raise ValueError("replay kind must be a non-empty string")
        provenance_record = record.get("provenance")
        provenance = None
        if provenance_record is not None:
            if not isinstance(provenance_record, Mapping):
                raise ValueError("replay provenance must be a mapping or null")
            source_type = provenance_record.get("source_type")
            source_ids = provenance_record.get("source_ids", ())
            source_sequences = provenance_record.get("source_sequences", ())
            p_timestamp = provenance_record.get("timestamp_ns", 0)
            confidence = provenance_record.get("confidence")
            if not isinstance(source_type, str) or not source_type:
                raise ValueError("replay provenance source_type must be a non-empty string")
            if not isinstance(source_ids, (list, tuple)) or not all(isinstance(x, str) for x in source_ids):
                raise ValueError("replay provenance source_ids must be strings")
            if not isinstance(source_sequences, (list, tuple)) or not all(isinstance(x, int) and not isinstance(x, bool) for x in source_sequences):
                raise ValueError("replay provenance source_sequences must be integers")
            if not isinstance(p_timestamp, int) or isinstance(p_timestamp, bool) or p_timestamp < 0:
                raise ValueError("replay provenance timestamp_ns must be non-negative")
            if confidence is not None and (not isinstance(confidence, (int, float)) or isinstance(confidence, bool)):
                raise ValueError("replay provenance confidence must be numeric or null")
            provenance = EventProvenance(
                source_type=source_type,
                source_ids=tuple(source_ids),
                source_sequences=tuple(source_sequences),
                timestamp_ns=p_timestamp,
                confidence=None if confidence is None else float(confidence),
                metadata=_decode_value(provenance_record.get("metadata")),
            )
        return cls(
            event_id=event_id,
            timestamp_ns=timestamp_ns,
            kind=kind,
            payload=_decode_value(record.get("payload")),
            provenance=provenance,
        )

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
        mismatches = []
        if not isinstance(record, dict):
            return ReplayValidation(
                valid=False,
                event_count=len(self._events),
                mismatches=("integrity.record: expected a mapping",),
            )
        try:
            version = int(record.get("version", -1))
            expected_count = int(record.get("event_count", -1))
        except (TypeError, ValueError):
            version = -1
            expected_count = -1
            mismatches.append("integrity.record: version/event_count must be integers")
        algorithm = record.get("algorithm", "")
        expected_digest = record.get("chain_digest", "")
        if not isinstance(algorithm, str):
            mismatches.append("integrity.algorithm: expected string")
            algorithm = ""
        if not isinstance(expected_digest, str):
            mismatches.append("integrity.chain_digest: expected string")
            expected_digest = ""
        if version != 1:
            mismatches.append("integrity.version: unsupported version " + str(version))
        if algorithm != "sha256":
            mismatches.append("integrity.algorithm: unsupported algorithm " + repr(algorithm))
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

    def persistent_state(self) -> dict[str, object]:
        """Serialize the complete replay chain and its integrity record."""
        return {
            "version": 1,
            "events": [event.to_record() for event in self._events],
            "integrity": self.integrity_record(),
        }

    @classmethod
    def from_persistent_state(cls, state: object) -> "ReplayLog":
        """Restore a replay log and reject any integrity mismatch."""
        if not isinstance(state, Mapping):
            raise ValueError("replay state must be a mapping")
        if state.get("version") != 1:
            raise ValueError("unsupported replay state version")
        records = state.get("events")
        if not isinstance(records, list):
            raise ValueError("replay state events must be a list")
        try:
            events = tuple(ReplayEvent.from_record(record) for record in records)
            log = cls(events)
        except (TypeError, ValueError, KeyError) as exc:
            raise ValueError(f"invalid replay event record: {exc}") from exc
        integrity = state.get("integrity")
        result = log.verify_integrity(integrity)
        if not result.valid:
            raise ValueError("replay integrity verification failed: " + "; ".join(result.mismatches))
        return log

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
\n\ndef _encode_value(value: object) -> object:\n    if value is None or isinstance(value, (str, int, float, bool)):\n        return value\n    if isinstance(value, Enum):\n        return {"__enum__": f"{type(value).__module__}.{type(value).__qualname__}", "value": _encode_value(value.value)}\n    if isinstance(value, Mapping):\n        return {"__mapping__": [[_encode_value(key), _encode_value(item)] for key, item in value.items()]}\n    if isinstance(value, tuple):\n        return {"__tuple__": [_encode_value(item) for item in value]}\n    if isinstance(value, list):\n        return [_encode_value(item) for item in value]\n    return {"__opaque_type__": f"{type(value).__module__}.{type(value).__qualname__}", "repr": repr(value)}\n\n\ndef _decode_value(value: object) -> object:\n    if isinstance(value, list):\n        return [_decode_value(item) for item in value]\n    if not isinstance(value, Mapping):\n        return value\n    if "__tuple__" in value:\n        return tuple(_decode_value(item) for item in value["__tuple__"])\n    if "__mapping__" in value:\n        return {_decode_value(pair[0]): _decode_value(pair[1]) for pair in value["__mapping__"]}\n    if "__opaque_type__" in value:\n        return dict(value)\n    if "__enum__" in value:\n        return {"__enum__": value["__enum__"], "value": _decode_value(value.get("value"))}\n    return {key: _decode_value(item) for key, item in value.items()}\n