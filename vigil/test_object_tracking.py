import pytest

from vigil.blueprint import register_blueprint
from vigil.object_tracking import ObjectObservation, ObjectTracker, TrackingModality


def observation(model, *, timestamp, position, sensor="rf-node-a",
                modality=TrackingModality.RF_2_4_GHZ, uncertainty=0.25,
                object_id="cart", frame=None):
    return ObjectObservation(
        object_id, sensor, model.model_id, model.revision,
        frame or model.frame_id, timestamp, position, uncertainty, modality,
        "calibrated-sensor-adapter",
    )


def test_tracker_fuses_rf_and_acoustic_sonar_positions_without_conflating_modalities():
    model = register_blueprint(
        "site", "r1", frame_id="site/building", units="m",
        features=[{"feature_id": "anchor", "label": "Anchor", "position": [0, 0, 0]}],
    )
    tracker = ObjectTracker()
    tracks = tracker.update(model, [
        observation(model, timestamp=100, position=(1, 2, 0), sensor="rf-node-a"),
        observation(model, timestamp=100, position=(1.2, 2, 0), sensor="sonar-a",
                    modality=TrackingModality.ACOUSTIC_SONAR),
    ], now_ns=110)
    assert len(tracks) == 1
    track = tracks[0]
    assert track.object_id == "cart"
    assert track.sensor_ids == ("rf-node-a", "sonar-a")
    assert track.modalities == ("acoustic_sonar", "rf_2_4ghz")
    assert track.uncertainty_m > 0


def test_tracker_estimates_velocity_and_expires_stale_or_wrong_frame_detections():
    model = register_blueprint(
        "site", "r1", frame_id="site/building", units="m",
        features=[{"feature_id": "anchor", "label": "Anchor", "position": [0, 0, 0]}],
    )
    tracker = ObjectTracker(alpha=1.0)
    tracker.update(model, [observation(model, timestamp=1_000_000_000, position=(0, 0, 0))],
                   now_ns=1_000_000_000)
    moved = tracker.update(
        model, [observation(model, timestamp=2_000_000_000, position=(2, 0, 0))],
        now_ns=2_000_000_000,
    )
    assert moved[0].position_m == (2.0, 0.0, 0.0)
    assert moved[0].velocity_mps == (2.0, 0.0, 0.0)
    empty = tracker.update(
        model,
        [observation(model, timestamp=3_000_000_000, position=(99, 0, 0), frame="wrong/frame")],
        now_ns=4_000_000_000, max_age_ns=500_000_000,
    )
    assert empty == ()


def test_tracker_rejects_invalid_modalities_and_uncertainty():
    model = register_blueprint(
        "site", "r1", frame_id="site/building", units="m",
        features=[{"feature_id": "anchor", "label": "Anchor", "position": [0, 0, 0]}],
    )
    with pytest.raises(ValueError, match="modality"):
        ObjectObservation(
            "cart", "sensor", model.model_id, model.revision, model.frame_id,
            1, (0, 0, 0), 0.1, "sonar", "test",
        )


def test_tracker_does_not_average_old_positions_into_latest_motion_epoch():
    model = register_blueprint(
        "site", "r1", frame_id="site/building", units="m",
        features=[{"feature_id": "anchor", "label": "Anchor", "position": [0, 0, 0]}],
    )
    tracker = ObjectTracker(alpha=1.0)
    tracker.update(
        model, [observation(model, timestamp=1_000_000_000, position=(0, 0, 0))],
        now_ns=1_000_000_000,
    )
    updated = tracker.update(
        model,
        [
            observation(model, timestamp=1_000_000_000, position=(0, 0, 0), sensor="old-sensor"),
            observation(model, timestamp=2_000_000_000, position=(2, 0, 0), sensor="new-sensor"),
        ],
        now_ns=2_000_000_000,
    )
    assert updated[0].position_m == pytest.approx((2, 0, 0))
    assert updated[0].velocity_mps == pytest.approx((2, 0, 0))
    assert updated[0].sensor_ids == ("new-sensor", "rf-node-a")



def test_tracker_fuses_ir_and_vision_only_with_explicit_shared_association():
    model = register_blueprint(
        "site", "r1", frame_id="site/building", units="m",
        features=[{"feature_id": "anchor", "label": "Anchor", "position": [0, 0, 0]}],
    )
    tracker = ObjectTracker()
    tracks = tracker.update(model, [
        ObjectObservation(
            "thermal-target-4", "thermal-1", model.model_id, model.revision,
            model.frame_id, 100, (1.0, 2.0, 0.0), 0.2,
            TrackingModality.INFRARED, "calibrated-thermal-detector",
            association_id="entity-42",
        ),
        ObjectObservation(
            "vision-track-9", "camera-2", model.model_id, model.revision,
            model.frame_id, 100, (1.1, 2.0, 0.0), 0.1,
            TrackingModality.VISION, "camera-reid-association",
            association_id="entity-42",
        ),
    ], now_ns=110)

    assert len(tracks) == 1
    track = tracks[0]
    assert track.association_id == "entity-42"
    assert track.object_id == "thermal-target-4"
    assert track.sensor_ids == ("camera-2", "thermal-1")
    assert track.modalities == ("infrared", "vision")
    assert track.provenance == ("calibrated-thermal-detector", "camera-reid-association")
    assert track.observation_count == 2
    assert track.position_m == pytest.approx((1.08, 2.0, 0.0))
    assert track.uncertainty_m == pytest.approx((1 / (1 / 0.2**2 + 1 / 0.1**2)) ** 0.5)


def test_tracker_does_not_merge_nearby_detections_without_shared_identity():
    model = register_blueprint(
        "site", "r1", frame_id="site/building", units="m",
        features=[{"feature_id": "anchor", "label": "Anchor", "position": [0, 0, 0]}],
    )
    tracks = ObjectTracker().update(model, [
        observation(model, timestamp=100, position=(1.0, 2.0, 0.0), object_id="vision-1",
                    sensor="camera", modality=TrackingModality.VISION),
        observation(model, timestamp=100, position=(1.01, 2.0, 0.0), object_id="thermal-1",
                    sensor="thermal", modality=TrackingModality.INFRARED),
    ], now_ns=110)
    assert len(tracks) == 2
    assert {track.object_id for track in tracks} == {"vision-1", "thermal-1"}
