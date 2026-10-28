"""ReplayLog consumer that routes trusted sinking events to the artifact bridge."""
from __future__ import annotations

from typing import Any, Callable

from .artifact_simulation_bridge import ArtifactSimulationBridge
from .simulation import ReplayEvent


class ArtifactReplayConsumer:
    """Adapt ReplayLog.replay_into() to authoritative unit-state lookups.

    The resolver must read current server-owned simulation state, not a browser
    payload. Non-sinking events are ignored; invalid sink events fail closed.
    """

    def __init__(self, *, world_seed: str, bridge: ArtifactSimulationBridge, resolve_unit_state: Callable[[str], Any]):
        if not isinstance(world_seed, str) or not world_seed.strip():
            raise ValueError("world_seed must be a non-empty string")
        if not isinstance(bridge, ArtifactSimulationBridge):
            raise TypeError("bridge must be an ArtifactSimulationBridge")
        if not callable(resolve_unit_state):
            raise TypeError("resolve_unit_state must be callable")
        self.world_seed = world_seed.strip()
        self.bridge = bridge
        self.resolve_unit_state = resolve_unit_state

    def attach(self, replay_log):
        """Subscribe this consumer to future authoritative ReplayLog appends.

        The log must be owned by the running simulation. This does not create
        sink events; it handles real UNIT_SUNK events once the simulation appends
        them. Historical replay remains an explicit operation.
        """
        from .simulation import ReplayLog

        if not isinstance(replay_log, ReplayLog):
            raise TypeError("replay_log must be a Coreless ReplayLog")
        return replay_log.subscribe(self)

    def __call__(self, event: ReplayEvent) -> list[dict[str, Any]] | None:
        if not isinstance(event, ReplayEvent):
            raise TypeError("consumer accepts Coreless ReplayEvent instances only")
        if event.kind not in ("UNIT_SUNK", "UNIT_REMOVED"):
            return None
        from collections.abc import Mapping
        if not isinstance(event.payload, Mapping):
            raise ValueError("artifact recovery replay payload must be a mapping")
        unit_id = event.payload.get("unit_id")
        if not isinstance(unit_id, str) or not unit_id.strip():
            raise ValueError("sinking replay event requires unit_id")
        if event.kind == "UNIT_SUNK":
            authoritative_state = self.resolve_unit_state(unit_id)
            if authoritative_state is None:
                raise ValueError("authoritative sunk-unit state is unavailable")
            return self.bridge.on_replay_event(self.world_seed, event, authoritative_state)

        # Removal deletes a unit from the live fleet, so a current-state resolver
        # may correctly return None. A server-owned ReplayLog removal event is a
        # tombstone: accept its last position only with simulation provenance,
        # strong confidence, matching source ID, and complete confirmed fields.
        provenance = event.provenance
        if (provenance is None or provenance.source_type != "simulation"
                or provenance.confidence is None or provenance.confidence < 0.8
                or unit_id not in provenance.source_ids):
            raise ValueError("unit-removal replay event requires trusted simulation provenance")
        payload = dict(event.payload)
        if payload.get("status") != "CONFIRMED":
            raise ValueError("unit removal requires a confirmed transition")
        payload["kind"] = "UNIT_REMOVED"
        payload["event_id"] = event.event_id
        tombstone = {
            "id": unit_id,
            "unitType": "submersible",
            "crewId": payload.get("crew_id"),
            "x": payload.get("x"),
            "y": payload.get("y"),
        }
        # If a resolver still knows the removed unit, cross-check its identity,
        # type, crew, and coordinates. Missing live state is expected after removal.
        live_state = self.resolve_unit_state(unit_id)
        if live_state is not None:
            for field, expected in (("id", unit_id), ("unitType", "submersible"),
                                    ("crewId", tombstone["crewId"]),
                                    ("x", tombstone["x"]), ("y", tombstone["y"])):
                if live_state.get(field) != expected:
                    raise ValueError("removal tombstone conflicts with authoritative unit state")
        return self.bridge.on_carrier_removed(self.world_seed, payload, tombstone)

    def reconcile_recorded_events(self, replay_log) -> dict[str, Any]:
        """Retry artifact recovery for already-recorded lifecycle events.

        ReplayLog is append-only, so a listener failure never erases the event.
        Re-running the ledger transition is safe: artifacts already dropped are
        no longer carried and therefore cannot be duplicated by a retry.
        """
        from .simulation import ReplayLog

        if not isinstance(replay_log, ReplayLog):
            raise TypeError("replay_log must be a Coreless ReplayLog")
        processed = 0
        ignored = 0
        recovered = 0
        failures = []
        for event in replay_log.events:
            if event.kind not in ("UNIT_SUNK", "UNIT_REMOVED"):
                ignored += 1
                continue
            try:
                result = self(event)
                processed += 1
                recovered += len(result or ())
            except Exception as exc:
                failures.append({"event_id": event.event_id, "kind": event.kind,
                                 "error": str(exc)})
        return {"processed": processed, "ignored": ignored,
                "recovered": recovered, "failures": failures}
