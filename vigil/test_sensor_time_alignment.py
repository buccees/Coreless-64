"""Tests for temporal grouping of VIGIL sensor evidence."""
import unittest

from vigil.sensor_event import SensorEventRecord, SensorEventStatus
from vigil.sensor_time_alignment import group_temporal_evidence


def event(event_id, timestamp, modality="vision", status=SensorEventStatus.ACCEPTED, **kwargs):
    return SensorEventRecord(
        event_id=event_id,
        sensor_id=kwargs.pop("sensor_id", f"{modality}-01"),
        timestamp_ns=timestamp,
        modality=modality,
        event_kind=kwargs.pop("event_kind", "observation"),
        status=status,
        reason=kwargs.pop("reason", "test observation"),
        **kwargs,
    )


class TemporalEvidenceGroupingTests(unittest.TestCase):
    def test_groups_events_within_aligned_window(self):
        camera = event("camera", 100, uncertainty_m=0.2, frame_id="floor-1")
        infrared = event("ir", 150, modality="infrared", uncertainty_m=0.4)
        groups = group_temporal_evidence(
            [infrared, camera],
            alignment_by_id={"ir": {"aligned_timestamp_ns": 110, "clock_offset_ns": -40}},
            window_ns=20,
        )
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["event_ids"], ["camera", "ir"])
        self.assertEqual(groups[0]["members"][1]["aligned_timestamp_ns"], 110)
        self.assertEqual(groups[0]["members"][0]["frame_id"], "floor-1")
        self.assertFalse(groups[0]["spatial_position_inferred"])

    def test_separates_events_outside_anchor_window(self):
        events = [event("a", 0), event("b", 8), event("c", 16)]
        groups = group_temporal_evidence(events, window_ns=10)
        self.assertEqual([g["event_ids"] for g in groups], [["a", "b"], ["c"]])

    def test_csi_is_context_and_never_a_position_fix(self):
        csi = event("csi", 10, modality="wifi_csi", status=SensorEventStatus.CONTEXT,
                    reason="CSI motion context only")
        groups = group_temporal_evidence([csi], window_ns=5)
        self.assertEqual(groups[0]["context_event_ids"], ["csi"])
        self.assertFalse(groups[0]["spatial_position_inferred"])
        self.assertEqual(groups[0]["members"][0]["reason"], "CSI motion context only")

    def test_preserves_source_lineage_without_claiming_independence(self):
        camera = event("camera", 100, modality="vision", sensor_id="cam-1",
                       independence_group="room-sensor-bus", lineage_declared=True)
        csi = event("csi", 105, modality="wifi_csi", status=SensorEventStatus.CONTEXT,
                    sensor_id="radio-1", independence_group="room-sensor-bus",
                    lineage_declared=True)
        unknown = event("unknown", 108, modality="infrared", sensor_id="ir-1")
        group = group_temporal_evidence([camera, csi, unknown], window_ns=20)[0]
        self.assertEqual(group["declared_independence_groups"], ["room-sensor-bus"])
        self.assertEqual(group["lineage_undeclared_event_ids"], ["unknown"])
        self.assertFalse(group["independent_corroboration_verified"])
        self.assertEqual(group["members"][0]["independence_group"], "room-sensor-bus")
        self.assertTrue(group["members"][0]["lineage_declared"])
        self.assertFalse(group["members"][2]["lineage_declared"])

    def test_output_order_is_deterministic_for_equal_timestamps(self):
        events = [event("z", 20), event("a", 20)]
        self.assertEqual(group_temporal_evidence(events, window_ns=0)[0]["event_ids"], ["a", "z"])

    def test_rejects_invalid_window_and_alignment(self):
        with self.assertRaises(ValueError):
            group_temporal_evidence([], window_ns=-1)
        with self.assertRaises(ValueError):
            group_temporal_evidence([event("bad", 10)],
                alignment_by_id={"bad": {"aligned_timestamp_ns": -1}})

    def test_rejects_duplicate_event_ids(self):
        with self.assertRaisesRegex(ValueError, "duplicate event_id"):
            group_temporal_evidence([event("same", 1), event("same", 2)])


if __name__ == "__main__":
    unittest.main()
