import math

import pytest

from vigil.blueprint import register_blueprint
from vigil.object_tracking import TrackingModality
from vigil.sensor_adapters import RangeMeasurement
from vigil.tracking_pipeline import RangeTrackingPipeline


def model():
    return register_blueprint(
        "site", "r1", frame_id="building/world", units="m",
        features=[{"feature_id": "anchor", "label": "Anchor", "position": [0, 0, 0]}],
    )


def ranges(active, target, timestamp=100, modality=TrackingModality.RF_2_4_GHZ):
    anchors = ((0, 0, 0), (10, 0, 0), (0, 10, 0), (0, 0, 10))
    return [
        RangeMeasurement(
            sensor_id=f"anchor-{i}", object_id="cart", model_id=active.model_id,
            model_revision=active.revision, frame_id=active.frame_id,
            timestamp_ns=timestamp, anchor_position_m=anchor,
            range_m=math.dist(anchor, target), uncertainty_m=0.05,
            modality=modality, provenance="calibrated-tof",
        )
        for i, anchor in enumerate(anchors)
    ]


def test_range_pipeline_creates_model_frame_track_from_calibrated_epoch():
    active = model()
    pipeline = RangeTrackingPipeline(active)
    tracks = pipeline.process_epoch(ranges(active, (2, 3, 4)), now_ns=100)
    assert len(tracks) == 1
    assert tracks[0].position_m == pytest.approx((2, 3, 4))
    assert tracks[0].modalities == (TrackingModality.RF_2_4_GHZ.value,)
    assert set(tracks[0].sensor_ids) == {"anchor-0", "anchor-1", "anchor-2", "anchor-3"}


def test_range_pipeline_keeps_distinct_objects_in_separate_tracks():
    active = model()
    pipeline = RangeTrackingPipeline(active)
    first = pipeline.process_epoch(ranges(active, (2, 3, 4)), now_ns=100)
    second = pipeline.process_epoch(ranges(active, (5, 6, 7), timestamp=200), now_ns=200)
    assert len(first) == len(second) == 1
    assert second[0].object_id == "cart"
    assert second[0].last_seen_ns == 200
    assert second[0].observation_count == 2


def test_range_pipeline_rejects_stale_or_wrong_model_epoch():
    active = model()
    pipeline = RangeTrackingPipeline(active, max_age_ns=10)
    with pytest.raises(ValueError, match="model/revision/frame"):
        wrong = list(ranges(active, (2, 3, 4)))
        item = wrong[0]
        wrong[0] = RangeMeasurement(
            sensor_id=item.sensor_id, object_id=item.object_id, model_id=item.model_id,
            model_revision=item.model_revision, frame_id="other/frame",
            timestamp_ns=item.timestamp_ns, anchor_position_m=item.anchor_position_m,
            range_m=item.range_m, uncertainty_m=item.uncertainty_m,
            modality=item.modality, provenance=item.provenance,
        )
        pipeline.process_epoch(wrong, now_ns=100)
    tracks = pipeline.process_epoch(ranges(active, (2, 3, 4), timestamp=1), now_ns=100)
    assert tracks == ()
