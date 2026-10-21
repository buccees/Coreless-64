import json

import pytest

from vigil.blueprint import register_blueprint
from vigil.positioning import SpatialObservation
from vigil.terminal import VigilTerminal
from vigil.workspace import BlueprintRegistry, SpatialWorkspace


def manifest(model_id="site-a", revision="r1", level="L1"):
    return json.dumps({
        "schema_version": 1, "model_id": model_id, "revision": revision,
        "frame_id": f"{model_id}/local", "units": "m",
        "features": [
            {"feature_id": "anchor", "label": "Anchor", "position": [0, 0, 0],
             "level": level, "zone": "north"},
            {"feature_id": "lift", "label": "Lift", "position": [4, 0, 0],
             "level": "L2", "zone": "core"},
        ],
    })


def observation(model, source, x=0.2, timestamp=100):
    return SpatialObservation(
        f"obs-{source}", source, model.model_id, model.revision, model.frame_id,
        timestamp, (x, 0, 0), 0.2, "workspace-test",
    )


def test_registry_imports_and_activates_manifest():
    registry = BlueprintRegistry()
    first = registry.import_json(manifest())
    second = registry.import_json(manifest("site-b", "r2"), activate=True)
    assert first.model_id == "site-a"
    assert registry.active_model == second
    assert len(registry.models) == 2


def test_registry_requires_revision_when_model_has_multiple_revisions():
    registry = BlueprintRegistry()
    registry.register(register_blueprint(
        "site", "r1", frame_id="site/local", units="m",
        features=[{"feature_id": "a", "label": "A", "position": [0, 0, 0]}],
    ))
    registry.register(register_blueprint(
        "site", "r2", frame_id="site/local", units="m",
        features=[{"feature_id": "a", "label": "A", "position": [1, 0, 0]}],
    ))
    with pytest.raises(ValueError, match="specify revision"):
        registry.activate("site")
    assert registry.activate("site", "r2").revision == "r2"


def test_workspace_selects_level_and_fuses_aligned_observations():
    workspace = SpatialWorkspace(terminal=VigilTerminal(color=False))
    model = workspace.import_blueprint(manifest(), activate=True)
    assert workspace.select_level("L1") == "L1"
    assert workspace.ingest([observation(model, "uwb"), observation(model, "vision", 0.25)]) == 2
    snapshot = workspace.refresh(now_ns=110)
    assert snapshot.model == model
    assert snapshot.selected_level == "L1"
    assert snapshot.pose is not None
    assert snapshot.pose.position_m is not None
    assert snapshot.pose.state.value == "TRACKING"
    rendered = workspace.render(now_ns=110)
    assert "L1" in rendered
    assert "TRACKING" in rendered


def test_workspace_shows_lost_when_no_fresh_observations():
    workspace = SpatialWorkspace(terminal=VigilTerminal(color=False))
    workspace.import_blueprint(manifest(), activate=True)
    snapshot = workspace.refresh(now_ns=10)
    assert snapshot.pose is not None
    assert snapshot.pose.position_m is None
    assert snapshot.pose.state.value == "LOST"


def test_workspace_rejects_unknown_level_and_does_not_transform_inputs():
    workspace = SpatialWorkspace()
    model = workspace.import_blueprint(manifest(), activate=True)
    with pytest.raises(KeyError, match="level not found"):
        workspace.select_level("L99")
    wrong_frame = SpatialObservation(
        "wrong", "uwb", model.model_id, model.revision, "device-frame", 100,
        (0, 0, 0), 0.2, "test",
    )
    workspace.ingest([wrong_frame])
    pose = workspace.refresh(now_ns=110).pose
    assert pose is not None and pose.position_m is None
