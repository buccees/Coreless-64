"""Tests for trusted, persistent sinking-event coordinates."""
import pytest

from vigil.sinking_event_registry import SinkingEventRegistry


def event(x=0.413, y=0.627, **changes):
    row = {"kind": "UNIT_SUNK", "status": "CONFIRMED", "event_id": "sink-01",
           "unit_id": "UUV-01", "x": x, "y": y}
    row.update(changes)
    return row


def unit(x=0.413, y=0.627, **changes):
    row = {"id": "UUV-01", "crewId": "crew-alpha", "unitType": "submersible",
           "afloat": False, "x": x, "y": y}
    row.update(changes)
    return row


def test_records_and_resolves_only_for_matching_crew_world_unit_and_event(tmp_path):
    registry = SinkingEventRegistry(tmp_path / "sinking.sqlite3")
    recorded = registry.record_from_simulation("PELAGOS-01", event(), unit())
    assert recorded["x"] == 0.413 and recorded["y"] == 0.627
    assert registry.resolve_sinking_event("crew-alpha", "PELAGOS-01", "UUV-01", "sink-01") == {
        "x": 0.413, "y": 0.627
    }
    assert registry.resolve_sinking_event("crew-beta", "PELAGOS-01", "UUV-01", "sink-01") is None
    assert registry.resolve_sinking_event("crew-alpha", "PELAGOS-02", "UUV-01", "sink-01") is None
    assert registry.resolve_sinking_event("crew-alpha", "PELAGOS-01", "UUV-02", "sink-01") is None
    assert registry.resolve_sinking_event("crew-alpha", "PELAGOS-01", "UUV-01", "fake-event") is None
    registry.close()


def test_rejects_unconfirmed_wrong_kind_or_floating_unit():
    registry = SinkingEventRegistry()
    with pytest.raises(ValueError, match="confirmed UNIT_SUNK"):
        registry.record_from_simulation("PELAGOS-01", event(status="INDICATED"), unit())
    with pytest.raises(ValueError, match="confirmed UNIT_SUNK"):
        registry.record_from_simulation("PELAGOS-01", event(kind="SONAR_CONTACT"), unit())
    with pytest.raises(ValueError, match="sunk submersible"):
        registry.record_from_simulation("PELAGOS-01", event(), unit(afloat=True))
    registry.close()


def test_rejects_stale_coordinates_nonfinite_positions_and_wrong_unit():
    registry = SinkingEventRegistry()
    with pytest.raises(ValueError, match="must match"):
        registry.record_from_simulation("PELAGOS-01", event(x=0.4), unit())
    with pytest.raises(ValueError, match="normalized finite"):
        registry.record_from_simulation("PELAGOS-01", event(x=float("nan")), unit(x=float("nan")))
    with pytest.raises(ValueError, match="authoritative unit"):
        registry.record_from_simulation("PELAGOS-01", event(), unit(id="UUV-OTHER"))
    registry.close()


def test_duplicate_event_is_idempotent_but_conflicting_reuse_is_rejected(tmp_path):
    registry = SinkingEventRegistry(tmp_path / "sinking.sqlite3")
    first = registry.record_from_simulation("PELAGOS-01", event(), unit())
    assert registry.record_from_simulation("PELAGOS-01", event(), unit()) == first
    with pytest.raises(ValueError, match="reused with conflicting"):
        registry.record_from_simulation("PELAGOS-01", event(x=0.5, y=0.5), unit(x=0.5, y=0.5))
    registry.close()


def test_records_survive_reopening_database(tmp_path):
    path = tmp_path / "sinking.sqlite3"
    first = SinkingEventRegistry(path)
    first.record_from_simulation("PELAGOS-01", event(), unit())
    first.close()
    second = SinkingEventRegistry(path)
    assert second.resolve_sinking_event("crew-alpha", "PELAGOS-01", "UUV-01", "sink-01") == {
        "x": 0.413, "y": 0.627
    }
    second.close()
