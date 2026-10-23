import pytest

from vigil.blueprint import register_blueprint
from vigil.object_tracking import ObjectTrack
from vigil.raster_calibration import RasterBlueprintCalibration, RasterControlPoint
from vigil.spatial_regions import SpatialRegion
from vigil.spatial_registry_store import SpatialRegistryStore


def model(revision="r1", units="ft"):
    return register_blueprint(
        "building-a", revision, frame_id="building/world", units=units,
        features=[
            {"feature_id": "entry", "label": "Entry", "position": [0, 0, 0], "level": "L1", "zone": "public"},
            {"feature_id": "lab", "label": "Lab", "position": [10, 4, 2], "level": "L1", "zone": "restricted"},
        ],
        metadata={"floor_elevations_m": {"L1": 0.0}, "notes": ["surveyed", "reviewed"]},
    )


def region(m):
    return SpatialRegion(
        "secure-room", "Secure room", m.model_id, m.revision, m.frame_id,
        ((0, 0), (2, 0), (2, 2), (0, 2)), 0, 3, "L1", "restricted",
    )


def calibration(m):
    return RasterBlueprintCalibration.fit(
        model_id=m.model_id, model_revision=m.revision, frame_id=m.frame_id,
        level_id="L1", elevation_m=0,
        control_points=(
            RasterControlPoint(0, 0, 0, 0, "origin"),
            RasterControlPoint(100, 0, 10, 0, "east"),
            RasterControlPoint(0, 100, 0, 10, "north"),
        ),
    )


def test_model_revision_and_normalized_geometry_round_trip_without_hash_drift():
    original = model()
    store = SpatialRegistryStore()
    try:
        store.save_model(original, activate=True)
        restored = store.load_model(original.model_id, original.revision)
        assert restored == original
        assert restored.source_sha256 == original.source_sha256
        assert restored.features == original.features
        assert store.active_model_ref == (original.model_id, original.revision)
        assert store.list_models() == (original,)
        store.save_model(original)
        with pytest.raises(ValueError, match="immutable"):
            store.save_model(model(revision=original.revision, units="m"))
    finally:
        store.close()


def test_regions_round_trip_and_are_immutable_within_revision():
    m = model()
    target = region(m)
    store = SpatialRegistryStore()
    try:
        store.save_model(m)
        assert store.save_region(target) == target
        assert store.load_regions(m.model_id, m.revision) == (target,)
        with pytest.raises(ValueError, match="immutable"):
            store.save_region(SpatialRegion(
                target.region_id, target.label, target.model_id, target.model_revision,
                target.frame_id, ((0, 0), (3, 0), (3, 3), (0, 3)), 0, 3,
                target.level, target.zone,
            ))
        assert store.delete_region(m.model_id, m.revision, target.region_id)
        assert store.load_regions(m.model_id, m.revision) == ()
    finally:
        store.close()


def test_calibrations_round_trip_and_recalibration_requires_a_new_identity():
    m = model()
    original = calibration(m)
    store = SpatialRegistryStore()
    try:
        store.save_calibration("raster-L1-cal-1", original)
        assert store.load_calibration("raster-L1-cal-1") == original
        assert store.load_calibration("missing") is None
        shifted = RasterBlueprintCalibration.fit(
            model_id=m.model_id, model_revision=m.revision, frame_id=m.frame_id,
            level_id="L1", elevation_m=0,
            control_points=(
                RasterControlPoint(0, 0, 1, 0), RasterControlPoint(100, 0, 11, 0),
                RasterControlPoint(0, 100, 1, 10),
            ),
        )
        with pytest.raises(ValueError, match="new ID"):
            store.save_calibration("raster-L1-cal-1", shifted)
        assert store.save_calibration("raster-L1-cal-2", shifted) == "raster-L1-cal-2"
    finally:
        store.close()


def test_stored_record_size_limit_and_invalid_input():
    with pytest.raises(ValueError, match="at least 256"):
        SpatialRegistryStore(max_record_bytes=1)
    original = model()
    store = SpatialRegistryStore(max_record_bytes=256)
    try:
        with pytest.raises(ValueError, match="exceeds"):
            store.save_model(original)
    finally:
        store.close()


def test_active_model_set_requires_registered_revision_and_sql_like_ids_are_data():
    m = model()
    store = SpatialRegistryStore()
    try:
        with pytest.raises(KeyError, match="unregistered"):
            store.set_active_model("x'; DELETE FROM spatial_models; --", "r1")
        store.save_model(m)
        store.set_active_model(m.model_id, m.revision)
        assert store.active_model_ref == (m.model_id, m.revision)
        assert store.load_model(m.model_id, m.revision) == m
    finally:
        store.close()


def test_object_tracks_round_trip_with_evidence_and_history_intact():
    active = model()
    track = ObjectTrack(
        object_id="cart-7", model_id=active.model_id,
        model_revision=active.revision, frame_id=active.frame_id,
        position_m=(2.0, 3.0, 0.0), velocity_mps=(0.0, 0.0, 0.0),
        uncertainty_m=0.2, last_seen_ns=100,
        sensor_ids=("uwb-array",), modalities=("uwb",), observation_count=2,
        provenance=("calibrated-ranging",), independence_groups=("uwb-array",),
        position_history_m=((50, (2.0, 3.0, 0.0)), (100, (2.0, 3.0, 0.0))),
        position_history_sensor_ids=((50, ("uwb-array",)), (100, ("uwb-array",))),
        calibration_status="verified", calibration_ids=("survey-1",),
        lineage_declared=True, presence_state="STALE",
    )
    store = SpatialRegistryStore()
    try:
        store.save_model(active, activate=True)
        assert store.save_object_tracks(active, (track,)) == 1
        restored = store.load_object_tracks(active.model_id, active.revision)
        assert restored == (track,)
    finally:
        store.close()
