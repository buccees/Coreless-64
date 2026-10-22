"""Tests for safe local VIGIL telemetry persistence."""
import unittest

from vigil.telemetry_store import TelemetryEvent, TelemetryStore


class TelemetryStoreTests(unittest.TestCase):
    def setUp(self):
        self.store = TelemetryStore()

    def tearDown(self):
        self.store.close()

    def test_round_trip_metadata_without_payload(self):
        event = TelemetryEvent(
            timestamp_ns=123, sensor_id="radio-1", event_kind="csi_sample",
            protocol="802.11", packet_length=128, channel_mhz=2437,
            signal_dbm=-51.5, motion_evidence=0.7, motion_active=True,
        )
        row_id = self.store.record(event)
        row = self.store.recent()[0]
        self.assertEqual(row["id"], row_id)
        self.assertEqual(row["sensor_id"], "radio-1")
        self.assertEqual(row["motion_active"], 1)
        self.assertNotIn("payload", row)

    def test_bound_parameters_keep_sql_like_sensor_ids_as_data(self):
        strange_id = "radio'; DROP TABLE telemetry_events; --"
        self.store.record(TelemetryEvent(
            timestamp_ns=1, sensor_id=strange_id, event_kind="packet",
            protocol="802.11", packet_length=64, channel_mhz=2412,
        ))
        self.assertEqual(self.store.recent(sensor_id=strange_id)[0]["sensor_id"], strange_id)
        self.store.record(TelemetryEvent(
            timestamp_ns=2, sensor_id="radio-2", event_kind="packet",
            protocol="802.11", packet_length=64, channel_mhz=2412,
        ))
        self.assertEqual(len(self.store.recent()), 2)

    def test_sensor_filter_and_limit_validation(self):
        for sensor in ("a", "b"):
            self.store.record(TelemetryEvent(
                timestamp_ns=1, sensor_id=sensor, event_kind="packet",
                protocol="802.11", packet_length=64, channel_mhz=2412,
            ))
        self.assertEqual(len(self.store.recent(sensor_id="a")), 1)
        with self.assertRaises(ValueError):
            self.store.recent(limit=0)

    def test_rejects_invalid_evidence_and_lengths(self):
        with self.assertRaises(ValueError):
            TelemetryEvent(0, "s", "packet", "802.11", -1, 2412)
        with self.assertRaises(ValueError):
            TelemetryEvent(0, "s", "csi", "802.11", 10, 2412, motion_evidence=1.1)


if __name__ == "__main__":
    unittest.main()
