import pytest

from vigil.blueprint import BlueprintModel, ModelFeature
from vigil.infrared_floor_mapping import InfraredFloorMapper, InfraredPixelSample
from vigil.object_tracking import ObjectObservation, TrackingModality
from vigil.raster_calibration import RasterBlueprintCalibration, RasterControlPoint
from vigil.workspace import SpatialWorkspace


def make_model():
    return BlueprintModel(
        model_id="facility", revision="r7", frame_id="facility/world",
        source_units="m",
        features=(ModelFeature("origin", "Origin", (0.0, 0.0, 0.0), level="L1"),),
        source_sha256="a" * 64,
    )


def make_ir_map(association_id=None):
    calibration = RasterBlueprintCalibration.fit(
        model_id="facility", model_revision="r7", frame_id="facility/world",
        level_id="L1", elevation_m=0.0,
        control_points=[
            RasterControlPoint(0, 0, 0, 0),
            RasterControlPoint(100, 0, 10, 0),
            RasterControlPoint(0, 100, 0, 10),
        ],
    )
    return InfraredFloorMapper(
        calibration, sensor_id="thermal-1", image_width=100, image_height=100
    ).map_frame(
        [InfraredPixelSample(20, 30, 0.9, temperature_c=38.0, label="target-1",
                             association_id=association_id),
         InfraredPixelSample(40, 40, 0.4)],
        timestamp_ns=100,
    )


def test_infrared_map_is_retained_and_labeled_detection_enters_shared_tracker():
    workspace = SpatialWorkspace()
    workspace.registry.register(make_model(), activate=True)
    ir_map = make_ir_map()

    assert workspace.ingest_infrared_map(ir_map) == 1
    snapshot = workspace.refresh(now_ns=100)

    assert snapshot.infrared_maps == (ir_map,)
    assert len(snapshot.object_tracks) == 1
    track = snapshot.object_tracks[0]
    assert track.object_id == "target-1"
    assert track.position_m == pytest.approx((2.0, 3.0, 0.0))
    assert "infrared" in track.modalities


def test_infrared_map_rejects_wrong_model_revision_or_frame():
    from dataclasses import replace
    workspace = SpatialWorkspace()
    workspace.registry.register(make_model(), activate=True)
    with pytest.raises(ValueError, match="active model"):
        workspace.ingest_infrared_map(replace(make_ir_map(), model_revision="stale"))


def test_untracked_infrared_samples_still_update_floor_layer():
    workspace = SpatialWorkspace()
    workspace.registry.register(make_model(), activate=True)
    ir_map = make_ir_map()
    assert workspace.ingest_infrared_map(ir_map, track_labeled_objects=False) == 0
    assert workspace.object_tracks == ()
    assert workspace.infrared_maps == (ir_map,)



def test_ir_floor_map_and_vision_detection_share_explicit_entity_association():
    workspace = SpatialWorkspace()
    model = make_model()
    workspace.registry.register(model, activate=True)
    ir_map = make_ir_map(association_id="entity-42")
    workspace.ingest_infrared_map(ir_map)
    workspace.ingest_object_observations([
        ObjectObservation(
            object_id="camera-track-7", sensor_id="camera-1",
            model_id=model.model_id, model_revision=model.revision,
            frame_id=model.frame_id, timestamp_ns=100,
            position_m=(2.1, 3.0, 0.0), uncertainty_m=0.1,
            modality=TrackingModality.VISION, provenance="vision-reid",
            association_id="entity-42",
        )
    ])

    snapshot = workspace.refresh(now_ns=100)
    assert len(snapshot.object_tracks) == 1
    track = snapshot.object_tracks[0]
    assert track.association_id == "entity-42"
    assert track.modalities == ("infrared", "vision")
    assert track.sensor_ids == ("camera-1", "thermal-1")
    assert track.provenance == ("calibrated-infrared-floor-map", "vision-reid")
