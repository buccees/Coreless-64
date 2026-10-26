"""Tests for normalized VIGIL sensor event records and ledger."""
import unittest

from vigil.sensor_event import SensorEventLedger, SensorEventRecord, SensorEventStatus


def make_event(event_id="evt-1", timestamp_ns=100, status=SensorEventStatus.ACCEPTED, **kwargs):
    kwargs.setdefault("confidence", 0.86)
    kwargs.setdefault("calibration_status", "demo_only")
    kwargs.setdefault("reason", "demo detection accepted")
    sensor_id = kwargs.pop("sensor_id", "cam-01")
    return SensorEventRecord(
        event_id=event_id,
        sensor_id=sensor_id,
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


    def test_ledger_rejects_out_of_order_timestamp_by_default(self):
        ledger = SensorEventLedger()
        ledger.append(make_event("newer", timestamp_ns=200, sequence=2))
        with self.assertRaisesRegex(ValueError, "late event"):
            ledger.append(make_event("older", timestamp_ns=150, sequence=3))
        self.assertEqual(len(ledger.snapshot(now_ns=500)), 1)

    def test_bounded_late_event_is_retained_with_alignment_warning(self):
        ledger = SensorEventLedger(allowed_lateness_ns=50)
        ledger.append(make_event("newer", timestamp_ns=200, sequence=2))
        ledger.append(make_event("slightly-late", timestamp_ns=175, sequence=3))
        self.assertEqual(ledger.alignment_for("slightly-late"), {
            "status": "late_within_tolerance",
            "reason": "event arrived behind the sensor watermark; retained with warning",
            "lateness_ns": 25,
            "clock_offset_ns": 0,
            "aligned_timestamp_ns": 175,
        })
        self.assertEqual(ledger.alignment_for("newer")["status"], "aligned")

    def test_ledger_rejects_non_increasing_sequence(self):
        ledger = SensorEventLedger()
        ledger.append(make_event("seq-4", timestamp_ns=100, sequence=4))
        with self.assertRaisesRegex(ValueError, "out-of-order sequence"):
            ledger.append(make_event("seq-3", timestamp_ns=110, sequence=3))

    def test_invalid_lateness_tolerance_is_rejected(self):
        with self.assertRaises(ValueError):
            SensorEventLedger(allowed_lateness_ns=-1)

    def test_explicit_clock_offsets_align_sensor_times_without_mutating_source(self):
        ledger = SensorEventLedger(clock_offsets_ns={"ir-01": 25})
        ledger.append(make_event("camera", timestamp_ns=200, sequence=1))
        ledger.append(make_event("ir", timestamp_ns=175, sequence=1, sensor_id="ir-01"))
        camera = ledger.alignment_for("camera")
        infrared = ledger.alignment_for("ir")
        self.assertEqual(camera["aligned_timestamp_ns"], 200)
        self.assertEqual(infrared["aligned_timestamp_ns"], 200)
        self.assertEqual(infrared["clock_offset_ns"], 25)
        self.assertEqual(ledger.snapshot(now_ns=200)[0].event_id, "ir")
        self.assertEqual(ledger.snapshot(now_ns=200)[1].event_id, "camera")

    def test_clock_offset_cannot_make_timestamp_negative(self):
        ledger = SensorEventLedger(clock_offsets_ns={"cam-01": -101})
        with self.assertRaisesRegex(ValueError, "negative aligned timestamp"):
            ledger.append(make_event(timestamp_ns=100))

    def test_clock_offset_must_be_integer_nanoseconds(self):
        with self.assertRaisesRegex(ValueError, "integer nanoseconds"):
            SensorEventLedger(clock_offsets_ns={"cam-01": 1.5})

if __name__ == "__main__":
    unittest.main()
