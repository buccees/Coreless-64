import pytest

from vigil.seafloor_campaign_store import SeafloorCampaignStore


def report(report_id="report-1", seed="PELAGOS-01"):
    return {
        "schema": "vigil.seafloor-survey",
        "version": 1,
        "report_id": report_id,
        "world_seed": seed,
        "coverage": ["4,7", "4,8", "4,7"],
        "discoveries": [{
            "id": "PELAGOS-01:entity:4,7",
            "kind": "SEAMOUNT",
            "x": 0.4,
            "y": 0.7,
            "scale": "LOCAL",
            "seed": seed,
            "status": "CONFIRMED",  # clients cannot confirm a site
            "discoveredAt": "2026-10-27T12:00:00Z",
            "depthMeters": 1400,
        }],
    }


def test_merge_is_persistent_and_export_is_seed_scoped(tmp_path):
    path = tmp_path / "campaign.sqlite3"
    store = SeafloorCampaignStore(path)
    try:
        result = store.merge_report(report(), crew_id="crew-alpha")
        assert result["coverage_added"] == 2
        assert result["discoveries_added"] == 1
    finally:
        store.close()

    reopened = SeafloorCampaignStore(path)
    try:
        exported = reopened.export_survey("PELAGOS-01")
        assert exported["coverage"] == ["4,7", "4,8"]
        assert len(exported["discoveries"]) == 1
        assert exported["discoveries"][0]["status"] == "SONAR INDICATION"
        assert reopened.export_survey("PELAGOS-02")["discoveries"] == []
    finally:
        reopened.close()


def test_retries_and_duplicate_discovery_ids_are_idempotent():
    store = SeafloorCampaignStore()
    try:
        first = store.merge_report(report(), crew_id="crew-alpha")
        retry = store.merge_report(report(), crew_id="crew-alpha")
        assert first["discoveries_added"] == 1
        assert retry["duplicate_report"] is True
        assert retry["discoveries_added"] == 0

        second = report("report-2")
        second["discoveries"][0]["id"] = "PELAGOS-01:entity:4,7"
        second["coverage"] = ["4,9"]
        merged = store.merge_report(second, crew_id="crew-bravo")
        assert merged["coverage_added"] == 1
        assert merged["discoveries_added"] == 0
        assert len(store.export_survey("PELAGOS-01")["discoveries"]) == 1
    finally:
        store.close()


def test_invalid_seed_coordinates_schema_and_untrusted_status_are_handled():
    store = SeafloorCampaignStore()
    try:
        wrong_seed = report()
        wrong_seed["discoveries"][0]["seed"] = "OTHER-WORLD"
        with pytest.raises(ValueError, match="world seed"):
            store.merge_report(wrong_seed, crew_id="crew-alpha")

        bad_coords = report("bad-coordinates")
        bad_coords["discoveries"][0]["x"] = float("nan")
        with pytest.raises(ValueError, match="finite normalized"):
            store.merge_report(bad_coords, crew_id="crew-alpha")

        bad_schema = report("bad-schema")
        bad_schema["schema"] = "unknown"
        with pytest.raises(ValueError, match="schema"):
            store.merge_report(bad_schema, crew_id="crew-alpha")

        accepted = store.merge_report(report(), crew_id="crew-alpha")
        assert accepted["ok"] is True
        assert store.export_survey("PELAGOS-01")["discoveries"][0]["status"] == "SONAR INDICATION"
    finally:
        store.close()


def test_report_size_limits_and_missing_authenticated_crew_are_rejected():
    store = SeafloorCampaignStore()
    try:
        with pytest.raises(ValueError, match="crew identity"):
            store.merge_report(report(), crew_id="")
        huge = report("too-many")
        huge["coverage"] = ["x"] * 100001
        with pytest.raises(ValueError, match="bounded"):
            store.merge_report(huge, crew_id="crew-alpha")
    finally:
        store.close()
