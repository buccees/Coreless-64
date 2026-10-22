"""Tests for normalized VIGIL sensor event records and ledger."""
import unittest

from vigil.sensor_event import SensorEventLedger, SensorEventRecord, SensorEventStatus


def make_event(event_id="evt-1", timestamp_ns=100, status=SensorEventStatus.ACCEPTED, **kwargs):
    kwargs.setdefault("confidence", 0.86)
    kwargs.setdefault("calibration_status", "demo_only")
    kwargs.setdefault("reason", "demo detection accepted")
    return SensorEventRecord(
        event_id=event_id,
        sensor_id="cam-01",
        timestamp_ns=timestamp_ns,
        modality="vision",
        event_kind="object_detection",
        status=status,
        **kwargs,
    )


class SensorEventTests(unittest.TestCase):
    def test_json_mapping_normalizes_enum_status(self):
        event = make_event()
        data = event.to_dict()
        self.assertEqual(data["status"], "accepted")
        self.assertEqual(data["timestamp_ns"], 100)
        self.assertEqual(data["confidence"], 0.86)

    def test_rejects_invalid_quality_fields(self):
        with self.assertRaises(ValueError):
            make_event(confidence=1.1)
        with self.assertRaises(ValueError):
            make_event(uncertainty_m=-0.1)
        with self.assertRaises(ValueError):
            make_event(timestamp_ns=-1)

    def test_ledger_orders_events_and_filters_stale_or_future(self):
        ledger = SensorEventLedger()
        ledger.append(make_event("old", timestamp_ns=10))
        ledger.append(make_event("fresh", timestamp_ns=95, sequence=3))
        ledger.append(make_event("future", timestamp_ns=101))
        snapshot = ledger.snapshot(now_ns=100, max_age_ns=20)
        self.assertEqual([item.event_id for item in snapshot], ["fresh"])

    def test_ledger_rejects_duplicate_event_ids(self):
        ledger = SensorEventLedger()
        ledger.append(make_event("same"))
        with self.assertRaises(ValueError):
            ledger.append(make_event("same", timestamp_ns=101))

    def test_rejected_event_keeps_reason_and_provenance(self):
        event = make_event(
            status=SensorEventStatus.REJECTED,
            reason="stale timestamp",
            model_id="blueprint-a",
            model_revision="r2",
            frame_id="level-00",
        )
        data = event.to_dict()
        self.assertEqual(data["status"], "rejected")
        self.assertEqual(data["reason"], "stale timestamp")
        self.assertEqual(data["frame_id"], "level-00")


if __name__ == "__main__":
    unittest.main()
