import json

import pytest

from vigil.object_tracking import ObjectObservation, TrackingModality
from vigil.spatial_regions import SpatialRegion
from vigil.spatial_snapshot import build_spatial_snapshot
from vigil.workspace import SpatialWorkspace
from vigil.positioning import SpatialObservation
from vigil.blueprint import register_blueprint


def model():
    return register_blueprint(
        "facility", "r1", frame_id="facility/world", units="m",
        features=[
            {"feature_id": "entry", "label": "Entry", "position": [0, 0, 0], "level": "L1", "zone": "public"},
            {"feature_id": "lab", "label": "Lab", "position": [10, 5, 0], "level": "L1", "zone": "restricted"},
            {"feature_id": "upper", "label": "Upper", "position": [10, 5, 3], "level": "L2", "zone": "research"},
        ],
    )


def test_snapshot_has_floor_geometry_pose_and_object_state_as_json_safe_data():
    workspace = SpatialWorkspace()
    active = model()
    workspace.registry.register(active, activate=True)
    workspace.select_level("L1")
    workspace.ingest([
        SpatialObservation("pose-uwb", "uwb-pose", active.model_id, active.revision,
                          active.frame_id, 100, (3.0, 2.0, 0.0), 0.2, "calibrated-test"),
        SpatialObservation("pose-vision", "vision-pose", active.model_id, active.revision,
                           active.frame_id, 100, (3.05, 2.0, 0.0), 0.2, "calibrated-test"),
    ])
    workspace.ingest_object_observations([ObjectObservation(
        "cart-7", "uwb-array", active.model_id, active.revision, active.frame_id,
        100, (3, 2, 0), 0.2, TrackingModality.UWB, "calibrated-ranging",
        independence_group="uwb-array", calibration_status="verified",
        calibration_ids=("site-survey-2026-10",), lineage_declared=True,
    )])
    snapshot = build_spatial_snapshot(workspace, now_ns=110)
    assert snapshot["protocol_version"] == 1
    assert snapshot["available"] is True
    assert snapshot["model"]["selected_level"] == "L1"
    assert [feature["feature_id"] for feature in snapshot["features"]] == ["entry", "lab"]
    marker = snapshot["objects"][0]
    assert marker["object_id"] == "cart-7"
    assert marker["presence_state"] == "TRACKING"
    assert marker["position_m"] == [3.0, 2.0, 0.0]
    assert marker["motion_state"] == "UNKNOWN"
    assert marker["last_seen_ns"] == "100"
    assert marker["provenance"] == ["calibrated-ranging"]
    assert marker["observation_count"] == 1
    assert marker["independence_groups"] == ["uwb-array"]
    assert marker["calibration_status"] == "verified"
    assert marker["calibration_ids"] == ["site-survey-2026-10"]
    assert marker["lineage_declared"] is True
    assert snapshot["spatial_query"]["status"] == "OK"
    assert snapshot["pose"]["presence_state"] == "CURRENT"
    assert snapshot["pose"]["observation_timestamp_ns"] == "100"
    assert snapshot["pose"]["age_ns"] == "10"
    assert json.loads(json.dumps(snapshot))["model"]["bounds_m"][0]["max"] == 10.0


def test_snapshot_preserves_stale_object_location_without_claiming_current_motion():
    workspace = SpatialWorkspace()
    active = model()
    workspace.registry.register(active, activate=True)
    workspace.ingest_object_observations([ObjectObservation(
        "stationary-crate", "uwb-array", active.model_id, active.revision, active.frame_id,
        100, (4, 2, 0), 0.2, TrackingModality.UWB, "calibrated-ranging",
    )])
    build_spatial_snapshot(workspace, now_ns=110)
    snapshot = build_spatial_snapshot(workspace, now_ns=3_000_000_000)
    marker = snapshot["objects"][0]
    assert marker["presence_state"] == "STALE"
    assert marker["motion_state"] == "UNKNOWN"
    assert marker["position_m"] == [4.0, 2.0, 0.0]
    assert marker["age_ns"] == "2999999900"


def test_snapshot_includes_explicit_region_membership_without_inventing_position():
    workspace = SpatialWorkspace()
    active = model()
    workspace.registry.register(active, activate=True)
    workspace.select_level("L1")
    region = SpatialRegion(
        "secure-zone", "Secure zone", active.model_id, active.revision, active.frame_id,
        ((0, 0), (5, 0), (5, 5), (0, 5)), 0, 2, "L1", "restricted",
    )
    workspace.register_region(region)
    result = build_spatial_snapshot(workspace, now_ns=110)
    assert result["regions"][0]["region_id"] == "secure-zone"
    assert result["regions"][0]["inside"] is None
    assert result["regions"][0]["status"] == "NO_FIX"


def test_snapshot_empty_workspace_is_valid_and_no_fake_geometry_is_added():
    snapshot = build_spatial_snapshot(SpatialWorkspace(), now_ns=0)
    assert snapshot["available"] is False
    assert snapshot["status"] == "no_blueprint"
    assert snapshot["model"] is None
    assert snapshot["features"] == []
    assert snapshot["objects"] == []


def test_snapshot_rejects_bad_time_and_wrong_workspace():
    with pytest.raises(ValueError):
        build_spatial_snapshot(SpatialWorkspace(), now_ns=-1)
    with pytest.raises(TypeError):
        build_spatial_snapshot(object(), now_ns=0)
