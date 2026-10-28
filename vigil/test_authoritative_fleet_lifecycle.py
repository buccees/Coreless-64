"""Tests for the server-owned fleet lifecycle publisher."""
import pytest

from vigil.authoritative_fleet_lifecycle import AuthoritativeFleetLifecycle


def unit(*, afloat=True, x=0.4, y=0.6):
    return {"id": "UUV-AUTH", "unitType": "submersible", "crewId": "crew-alpha",
            "afloat": afloat, "x": x, "y": y}


def test_confirmed_sinking_publishes_server_resolved_state():
    current = unit(afloat=False, x=0.25, y=0.75)
    source = AuthoritativeFleetLifecycle(lambda unit_id: current if unit_id == current["id"] else None)
    seen = []
    source.subscribe_lifecycle(seen.append)

    event = source.confirm_sunk(event_id="sink-1", timestamp_ns=10, unit_id="UUV-AUTH")

    assert event["kind"] == "UNIT_SUNK"
    assert event["status"] == "CONFIRMED"
    assert event["final_unit_state"]["afloat"] is False
    assert (event["x"], event["y"]) == (0.25, 0.75)
    assert seen == [event]


def test_sinking_requires_committed_sunk_state_and_unique_event_id():
    current = unit(afloat=True)
    source = AuthoritativeFleetLifecycle(lambda unit_id: current)
    with pytest.raises(ValueError, match="committed sunk state"):
        source.confirm_sunk(event_id="sink-pending", timestamp_ns=10, unit_id="UUV-AUTH")

    current["afloat"] = False
    source.confirm_sunk(event_id="sink-confirmed", timestamp_ns=11, unit_id="UUV-AUTH")
    with pytest.raises(ValueError, match="already been published"):
        source.confirm_sunk(event_id="sink-confirmed", timestamp_ns=12, unit_id="UUV-AUTH")


def test_removal_publishes_final_snapshot_after_live_unit_disappears():
    live = {"UUV-AUTH": unit(x=0.2, y=0.3)}
    source = AuthoritativeFleetLifecycle(lambda unit_id: live.get(unit_id))
    seen = []
    source.subscribe_lifecycle(seen.append)

    final_state = dict(live.pop("UUV-AUTH"))
    final_state.update(x=0.91, y=0.17)
    event = source.confirm_removed(event_id="remove-1", timestamp_ns=20,
                                   unit_id="UUV-AUTH", final_unit_state=final_state)

    assert source._resolve_unit_state("UUV-AUTH") is None
    assert event["kind"] == "UNIT_REMOVED"
    assert event["final_unit_state"]["crewId"] == "crew-alpha"
    assert (event["x"], event["y"]) == (0.91, 0.17)
    assert seen == [event]


@pytest.mark.parametrize("bad", [
    {"id": "UUV-AUTH", "unitType": "submersible", "crewId": "", "x": 0.2, "y": 0.3},
    {"id": "UUV-AUTH", "unitType": "submersible", "crewId": "crew-alpha", "x": float("nan"), "y": 0.3},
    {"id": "OTHER", "unitType": "submersible", "crewId": "crew-alpha", "x": 0.2, "y": 0.3},
])
def test_removal_rejects_invalid_final_snapshot(bad):
    source = AuthoritativeFleetLifecycle(lambda unit_id: None)
    with pytest.raises(ValueError):
        source.confirm_removed(event_id="remove-invalid", timestamp_ns=20,
                               unit_id="UUV-AUTH", final_unit_state=bad)
