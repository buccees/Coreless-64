"""Server-owned publisher for committed fleet lifecycle transitions.

Combat/fleet managers call this only after their authoritative state transaction
has committed. The publisher emits immutable-by-copy transition snapshots for
VIGIL artifact recovery and other server-side consumers; browser events are not
accepted as lifecycle input.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
import math
from typing import Any


class AuthoritativeFleetLifecycle:
    """Publish confirmed sinking/removal transitions from server-owned state."""

    def __init__(self, resolve_unit_state: Callable[[str], Mapping[str, Any] | None]):
        if not callable(resolve_unit_state):
            raise TypeError("resolve_unit_state must be callable")
        self._resolve_unit_state = resolve_unit_state
        self._listeners: list[Callable[[dict[str, Any]], Any]] = []
        self._event_ids: set[str] = set()

    def subscribe_lifecycle(self, callback: Callable[[dict[str, Any]], Any]) -> Callable[[], None]:
        if not callable(callback):
            raise TypeError("lifecycle subscriber must be callable")
        self._listeners.append(callback)
        def unsubscribe() -> None:
            if callback in self._listeners:
                self._listeners.remove(callback)
        return unsubscribe

    @staticmethod
    def _identity(event_id: str, timestamp_ns: int, unit_id: str) -> None:
        if not isinstance(event_id, str) or not event_id.strip():
            raise ValueError("event_id must be a non-empty string")
        if not isinstance(unit_id, str) or not unit_id.strip():
            raise ValueError("unit_id must be a non-empty string")
        if not isinstance(timestamp_ns, int) or isinstance(timestamp_ns, bool) or timestamp_ns < 0:
            raise ValueError("timestamp_ns must be a non-negative integer")

    @staticmethod
    def _snapshot(unit_id: str, state: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(state, Mapping) or str(state.get("id", "")) != unit_id:
            raise ValueError("lifecycle state must match the authoritative unit")
        if state.get("unitType") != "submersible":
            raise ValueError("artifact lifecycle supports submersibles only")
        crew_id = state.get("crewId")
        if not isinstance(crew_id, str) or not crew_id.strip():
            raise ValueError("authoritative submersible crew ID is required")
        x, y = state.get("x"), state.get("y")
        if isinstance(x, bool) or isinstance(y, bool):
            raise ValueError("authoritative coordinates must be numeric")
        try:
            x, y = float(x), float(y)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("authoritative coordinates must be numeric") from exc
        if not all(math.isfinite(v) and 0 <= v <= 1 for v in (x, y)):
            raise ValueError("authoritative coordinates must be normalized finite values")
        return {"id": unit_id, "unitType": "submersible", "crewId": crew_id.strip(),
                "x": x, "y": y, "afloat": state.get("afloat")}

    def _publish(self, *, kind: str, event_id: str, timestamp_ns: int,
                 unit_id: str, state: Mapping[str, Any]) -> dict[str, Any]:
        self._identity(event_id, timestamp_ns, unit_id)
        if event_id in self._event_ids:
            raise ValueError("lifecycle event_id has already been published")
        snapshot = self._snapshot(unit_id, state)
        if kind == "UNIT_SUNK" and snapshot["afloat"] is not False:
            raise ValueError("sinking must follow a committed sunk state")
        event = {
            "kind": kind, "status": "CONFIRMED", "event_id": event_id.strip(),
            "timestamp_ns": timestamp_ns, "unit_id": unit_id.strip(),
            "crew_id": snapshot["crewId"], "x": snapshot["x"], "y": snapshot["y"],
            "final_unit_state": dict(snapshot),
        }
        # Reserve the event ID before callbacks to prevent re-entrant duplicates.
        self._event_ids.add(event["event_id"])
        try:
            for listener in tuple(self._listeners):
                listener(dict(event))
        except Exception:
            # The source transition remains committed; caller can retry through
            # its persistent replay/reconciliation path, not publish a fake event.
            raise
        return event

    def confirm_sunk(self, *, event_id: str, timestamp_ns: int, unit_id: str) -> dict[str, Any]:
        """Publish only after the combat system has committed afloat=False."""
        state = self._resolve_unit_state(unit_id)
        if state is None:
            raise ValueError("authoritative sunk-unit state is unavailable")
        return self._publish(kind="UNIT_SUNK", event_id=event_id,
                             timestamp_ns=timestamp_ns, unit_id=unit_id, state=state)

    def confirm_removed(self, *, event_id: str, timestamp_ns: int,
                        unit_id: str, final_unit_state: Mapping[str, Any]) -> dict[str, Any]:
        """Publish the final server snapshot after removing a unit from the live fleet."""
        # Removal is allowed to make the resolver return None; use only the
        # final snapshot captured by the authoritative fleet manager at commit.
        return self._publish(kind="UNIT_REMOVED", event_id=event_id,
                             timestamp_ns=timestamp_ns, unit_id=unit_id,
                             state=final_unit_state)
