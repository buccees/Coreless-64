import pytest

from vigil.blueprint import register_blueprint
from vigil.object_tracking import ObjectObservation, ObjectTracker, TrackingModality


def observation(model, *, timestamp, position, sensor="rf-node-a",
                modality=TrackingModality.RF_2_4_GHZ, uncertainty=0.25,
                object_id="cart", frame=None, independence_group=None):
    return ObjectObservation(
        object_id, sensor, model.model_id, model.revision,
        frame or model.frame_id, timestamp, position, uncertainty, modality,
        "calibrated-sensor-adapter", independence_group=independence_group,
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



def test_tracker_flags_position_conflict_without_averaging_targets_to_midpoint():
    model = register_blueprint(
        "site", "r1", frame_id="site/building", units="m",
        features=[{"feature_id": "anchor", "label": "Anchor", "position": [0, 0, 0]}],
    )
    tracks = ObjectTracker().update(model, [
        ObjectObservation(
            "thermal-target", "thermal", model.model_id, model.revision,
            model.frame_id, 1_000_000_000, (0.0, 0.0, 0.0), 0.1,
            TrackingModality.INFRARED, "thermal-detector", association_id="entity-1",
        ),
        ObjectObservation(
            "vision-target", "camera", model.model_id, model.revision,
            model.frame_id, 1_000_000_000, (10.0, 0.0, 0.0), 0.2,
            TrackingModality.VISION, "vision-reid", association_id="entity-1",
        ),
    ], now_ns=1_000_000_000)

    assert len(tracks) == 1
    track = tracks[0]
    assert track.conflict is True
    assert track.conflict_reasons == ("position_disagreement",)
    assert track.conflicting_sensor_ids == ("camera", "thermal")
    assert track.position_m == pytest.approx((0.0, 0.0, 0.0))
    assert track.position_m != pytest.approx((5.0, 0.0, 0.0))


def test_tracker_flags_excessive_timestamp_skew_on_shared_identity():
    model = register_blueprint(
        "site", "r1", frame_id="site/building", units="m",
        features=[{"feature_id": "anchor", "label": "Anchor", "position": [0, 0, 0]}],
    )
    tracks = ObjectTracker(max_fusion_skew_ns=50_000_000).update(model, [
        ObjectObservation(
            "thermal-target", "thermal", model.model_id, model.revision,
            model.frame_id, 900_000_000, (1.0, 0.0, 0.0), 0.1,
            TrackingModality.INFRARED, "thermal-detector", association_id="entity-1",
        ),
        ObjectObservation(
            "vision-target", "camera", model.model_id, model.revision,
            model.frame_id, 1_000_000_000, (1.0, 0.0, 0.0), 0.2,
            TrackingModality.VISION, "vision-reid", association_id="entity-1",
        ),
    ], now_ns=1_000_000_000)

    assert len(tracks) == 1
    assert tracks[0].conflict is True
    assert tracks[0].conflict_reasons == ("timestamp_skew",)
    assert tracks[0].conflicting_sensor_ids == ("camera", "thermal")
    assert tracks[0].position_m == pytest.approx((1.0, 0.0, 0.0))


def test_tracker_clears_conflict_flag_when_new_consistent_epoch_arrives():
    model = register_blueprint(
        "site", "r1", frame_id="site/building", units="m",
        features=[{"feature_id": "anchor", "label": "Anchor", "position": [0, 0, 0]}],
    )
    tracker = ObjectTracker(alpha=1.0)
    tracker.update(model, [
        ObjectObservation(
            "thermal-target", "thermal", model.model_id, model.revision,
            model.frame_id, 1_000_000_000, (0.0, 0.0, 0.0), 0.1,
            TrackingModality.INFRARED, "thermal-detector", association_id="entity-1",
        ),
        ObjectObservation(
            "vision-target", "camera", model.model_id, model.revision,
            model.frame_id, 1_000_000_000, (10.0, 0.0, 0.0), 0.1,
            TrackingModality.VISION, "vision-reid", association_id="entity-1",
        ),
    ], now_ns=1_000_000_000)
    clean = tracker.update(model, [
        ObjectObservation(
            "thermal-target", "thermal", model.model_id, model.revision,
            model.frame_id, 2_000_000_000, (2.0, 0.0, 0.0), 0.1,
            TrackingModality.INFRARED, "thermal-detector", association_id="entity-1",
        ),
        ObjectObservation(
            "vision-target", "camera", model.model_id, model.revision,
            model.frame_id, 2_000_000_000, (2.1, 0.0, 0.0), 0.1,
            TrackingModality.VISION, "vision-reid", association_id="entity-1",
        ),
    ], now_ns=2_000_000_000)

    assert clean[0].conflict is False
    assert clean[0].conflict_reasons == ()
    assert clean[0].conflicting_sensor_ids == ()




def test_tracker_requires_multi_sensor_corroboration_to_clear_conflict():
    model = register_blueprint(
        "site", "r1", frame_id="site/building", units="m",
        features=[{"feature_id": "anchor", "label": "Anchor", "position": [0, 0, 0]}],
    )
    tracker = ObjectTracker(alpha=1.0)
    tracker.update(model, [
        ObjectObservation(
            "thermal-target", "thermal", model.model_id, model.revision,
            model.frame_id, 1_000_000_000, (0.0, 0.0, 0.0), 0.1,
            TrackingModality.INFRARED, "thermal-detector", association_id="entity-1",
        ),
        ObjectObservation(
            "vision-target", "camera", model.model_id, model.revision,
            model.frame_id, 1_000_000_000, (10.0, 0.0, 0.0), 0.1,
            TrackingModality.VISION, "vision-reid", association_id="entity-1",
        ),
    ], now_ns=1_000_000_000)

    single_sensor = tracker.update(model, [
        ObjectObservation(
            "thermal-target", "thermal", model.model_id, model.revision,
            model.frame_id, 2_000_000_000, (1.0, 0.0, 0.0), 0.1,
            TrackingModality.INFRARED, "thermal-detector", association_id="entity-1",
        ),
    ], now_ns=2_000_000_000)
    assert single_sensor[0].conflict is True
    assert "position_disagreement" in single_sensor[0].conflict_reasons
    assert single_sensor[0].conflicting_sensor_ids == ("camera", "thermal")

    corroborated = tracker.update(model, [
        ObjectObservation(
            "thermal-target", "thermal", model.model_id, model.revision,
            model.frame_id, 3_000_000_000, (2.0, 0.0, 0.0), 0.1,
            TrackingModality.INFRARED, "thermal-detector", association_id="entity-1",
        ),
        ObjectObservation(
            "vision-target", "camera", model.model_id, model.revision,
            model.frame_id, 3_000_000_000, (2.1, 0.0, 0.0), 0.1,
            TrackingModality.VISION, "vision-reid", association_id="entity-1",
        ),
    ], now_ns=3_000_000_000)
    assert corroborated[0].conflict is False
    assert corroborated[0].conflict_reasons == ()
    assert corroborated[0].conflicting_sensor_ids == ()


def test_shared_evidence_group_does_not_count_as_independent_corroboration():
    model = register_blueprint(
        "site", "r1", frame_id="site/building", units="m",
        features=[{"feature_id": "anchor", "label": "Anchor", "position": [0, 0, 0]}],
    )
    tracker = ObjectTracker(alpha=1.0)
    tracker.update(model, [
        ObjectObservation(
            "thermal-target", "thermal", model.model_id, model.revision,
            model.frame_id, 1_000_000_000, (0.0, 0.0, 0.0), 0.1,
            TrackingModality.INFRARED, "derived-feed-a", association_id="entity-1",
        ),
        ObjectObservation(
            "vision-target", "camera", model.model_id, model.revision,
            model.frame_id, 1_000_000_000, (10.0, 0.0, 0.0), 0.1,
            TrackingModality.VISION, "derived-feed-b", association_id="entity-1",
        ),
    ], now_ns=1_000_000_000)

    same_source = tracker.update(model, [
        ObjectObservation(
            "thermal-target", "thermal", model.model_id, model.revision,
            model.frame_id, 2_000_000_000, (2.0, 0.0, 0.0), 0.1,
            TrackingModality.INFRARED, "derived-feed-a", association_id="entity-1",
            independence_group="shared-receiver",
        ),
        ObjectObservation(
            "vision-target", "camera", model.model_id, model.revision,
            model.frame_id, 2_000_000_000, (2.1, 0.0, 0.0), 0.1,
            TrackingModality.VISION, "derived-feed-b", association_id="entity-1",
            independence_group="shared-receiver",
        ),
    ], now_ns=2_000_000_000)

    assert same_source[0].conflict is True
    assert same_source[0].independence_groups == ("camera", "shared-receiver", "thermal")


def test_independent_groups_can_clear_conflict_and_are_exposed_on_track():
    model = register_blueprint(
        "site", "r1", frame_id="site/building", units="m",
        features=[{"feature_id": "anchor", "label": "Anchor", "position": [0, 0, 0]}],
    )
    tracker = ObjectTracker(alpha=1.0)
    tracker.update(model, [
        ObjectObservation(
            "thermal-target", "thermal", model.model_id, model.revision,
            model.frame_id, 1_000_000_000, (0.0, 0.0, 0.0), 0.1,
            TrackingModality.INFRARED, "thermal-detector", association_id="entity-1",
        ),
        ObjectObservation(
            "vision-target", "camera", model.model_id, model.revision,
            model.frame_id, 1_000_000_000, (10.0, 0.0, 0.0), 0.1,
            TrackingModality.VISION, "vision-reid", association_id="entity-1",
        ),
    ], now_ns=1_000_000_000)

    tracks = tracker.update(model, [
        ObjectObservation(
            "thermal-target", "thermal", model.model_id, model.revision,
            model.frame_id, 2_000_000_000, (2.0, 0.0, 0.0), 0.1,
            TrackingModality.INFRARED, "thermal-detector", association_id="entity-1",
            independence_group="thermal-chain",
        ),
        ObjectObservation(
            "vision-target", "camera", model.model_id, model.revision,
            model.frame_id, 2_000_000_000, (2.1, 0.0, 0.0), 0.1,
            TrackingModality.VISION, "vision-reid", association_id="entity-1",
            independence_group="vision-chain",
        ),
    ], now_ns=2_000_000_000)

    assert tracks[0].conflict is False
    assert tracks[0].independence_groups == ("camera", "thermal", "thermal-chain", "vision-chain")


def test_tracker_rejects_blank_independence_group():
    model = register_blueprint(
        "site", "r1", frame_id="site/building", units="m",
        features=[{"feature_id": "anchor", "label": "Anchor", "position": [0, 0, 0]}],
    )
    with pytest.raises(ValueError, match="independence_group"):
        ObjectObservation(
            "cart", "sensor", model.model_id, model.revision, model.frame_id,
            1, (0, 0, 0), 0.1, TrackingModality.VISION, "test",
            independence_group="   ",
        )


def test_tracker_validates_conflict_resolution_sensor_threshold():
    with pytest.raises(ValueError, match="conflict_resolution_min_sensors"):
        ObjectTracker(conflict_resolution_min_sensors=1)


def test_tracker_does_not_drop_same_timestamp_conflict_after_initial_detection():
    model = register_blueprint(
        "site", "r1", frame_id="site/building", units="m",
        features=[{"feature_id": "anchor", "label": "Anchor", "position": [0, 0, 0]}],
    )
    tracker = ObjectTracker()
    first = ObjectObservation(
        "thermal-target", "thermal", model.model_id, model.revision,
        model.frame_id, 1_000_000_000, (0.0, 0.0, 0.0), 0.1,
        TrackingModality.INFRARED, "thermal-detector", association_id="entity-1",
    )
    tracker.update(model, [first], now_ns=1_000_000_000)
    conflicting = ObjectObservation(
        "vision-target", "camera", model.model_id, model.revision,
        model.frame_id, 1_000_000_000, (10.0, 0.0, 0.0), 0.1,
        TrackingModality.VISION, "vision-reid", association_id="entity-1",
    )

    tracks = tracker.update(model, [first, conflicting], now_ns=1_000_000_000)

    assert len(tracks) == 1
    assert tracks[0].conflict is True
    assert tracks[0].conflict_reasons == ("position_disagreement",)
    assert tracks[0].conflicting_sensor_ids == ("camera", "thermal")


def test_tracker_exposes_bounded_timestamped_motion_trail_in_model_frame():
    model = register_blueprint(
        "site", "r1", frame_id="site/building", units="m",
        features=[{"feature_id": "anchor", "label": "Anchor", "position": [0, 0, 0]}],
    )
    tracker = ObjectTracker(alpha=1.0, max_history_points=2)
    for timestamp, x in ((1_000_000_000, 0.0), (2_000_000_000, 2.0), (3_000_000_000, 5.0)):
        tracks = tracker.update(
            model, [observation(model, timestamp=timestamp, position=(x, 0.0, 0.0))],
            now_ns=timestamp,
        )
    trail = tracks[0].position_history_m
    assert trail == (
        (2_000_000_000, (2.0, 0.0, 0.0)),
        (3_000_000_000, (5.0, 0.0, 0.0)),
    )

def test_workspace_retention_marks_last_known_objects_stale_without_calling_them_gone():
    model = register_blueprint(
        "site", "r1", frame_id="site/building", units="m",
        features=[{"feature_id": "anchor", "label": "Anchor", "position": [0, 0, 0]}],
    )
    tracker = ObjectTracker(alpha=1.0)
    first = tracker.update(
        model, [observation(model, timestamp=100, position=(2, 3, 0))],
        now_ns=100, max_age_ns=50, retain_stale=True,
    )
    assert first[0].presence_state == "TRACKING"

    stale = tracker.update(
        model, [], now_ns=200, max_age_ns=50, retain_stale=True,
    )
    assert len(stale) == 1
    assert stale[0].presence_state == "STALE"
    assert stale[0].position_m == (2.0, 3.0, 0.0)
    assert stale[0].last_seen_ns == 100
    assert stale[0].observation_count == 1

    # Compatibility mode continues to expire stale tracks by default.
    expired = ObjectTracker(alpha=1.0)
    expired.update(model, [observation(model, timestamp=100, position=(2, 3, 0))], now_ns=100)
    assert expired.update(model, [], now_ns=200, max_age_ns=50) == ()


def test_retained_track_is_not_carried_into_a_different_model_frame():
    first_model = register_blueprint(
        "site", "r1", frame_id="site/building", units="m",
        features=[{"feature_id": "anchor", "label": "Anchor", "position": [0, 0, 0]}],
    )
    second_model = register_blueprint(
        "site", "r2", frame_id="site/revised-building", units="m",
        features=[{"feature_id": "anchor", "label": "Anchor", "position": [0, 0, 0]}],
    )
    tracker = ObjectTracker()
    tracker.update(
        first_model, [observation(first_model, timestamp=100, position=(2, 3, 0))],
        now_ns=100, retain_stale=True,
    )
    assert tracker.update(second_model, [], now_ns=200, retain_stale=True) == ()


def test_retained_track_marks_clock_reversal_as_time_uncertain():
    model = register_blueprint(
        "site", "r1", frame_id="site/building", units="m",
        features=[{"feature_id": "anchor", "label": "Anchor", "position": [0, 0, 0]}],
    )
    tracker = ObjectTracker()
    tracker.update(
        model, [observation(model, timestamp=200, position=(1, 0, 0))],
        now_ns=200, retain_stale=True,
    )
    result = tracker.update(model, [], now_ns=100, retain_stale=True)
    assert len(result) == 1
    assert result[0].presence_state == "TIME_UNCERTAIN"

