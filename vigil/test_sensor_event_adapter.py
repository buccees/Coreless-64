"""Tests for adapters from VIGIL telemetry into normalized sensor events."""
import unittest

from vigil.csi_pipeline import CsiPipelineResult
from vigil.rf_csi import CsiFeatures, MotionState
from vigil.sensor_event import SensorEventStatus
from vigil.sensor_event_adapter import csi_result_to_sensor_event, telemetry_to_sensor_event
from vigil.telemetry_store import TelemetryEvent


class SensorEventAdapterTests(unittest.TestCase):
    def test_csi_result_is_context_not_a_position_fix(self):
        result = CsiPipelineResult(
            timestamp_ns=1234,
            sensor_id="wifi-24-01",
            channel_mhz=2412,
            features=CsiFeatures(8, 0.1, 0.2, 0.03, 0.4),
            motion=MotionState(0.37, True, 3, 0),
            telemetry_row_id=17,
        )
        event = csi_result_to_sensor_event(result)
        self.assertEqual(event.event_id, "csi:wifi-24-01:1234:17")
        self.assertEqual(event.status, SensorEventStatus.CONTEXT)
        self.assertEqual(event.modality, "wifi_csi")
        self.assertEqual(event.evidence_score, 0.37)
        self.assertIsNone(event.confidence)
        self.assertIsNone(event.uncertainty_m)
        self.assertIn("not a position fix", event.reason)
        self.assertEqual(event.sequence, 17)

    def test_telemetry_adapter_preserves_only_supplied_values(self):
        source = TelemetryEvent(
            timestamp_ns=99, sensor_id="router-csi", event_kind="csi_motion_evidence",
            protocol="802.11", packet_length=80, channel_mhz=2412,
            signal_dbm=-51.0, motion_evidence=0.62, motion_active=True,
        )
        event = telemetry_to_sensor_event(source, sequence=4)
        self.assertEqual(event.status, SensorEventStatus.CONTEXT)
        self.assertEqual(event.signal_dbm, -51.0)
        self.assertEqual(event.evidence_score, 0.62)
        self.assertEqual(event.sequence, 4)
        self.assertIsNone(event.confidence)
        self.assertIsNone(event.frame_id)

    def test_non_csi_telemetry_is_not_labeled_as_csi(self):
        source = TelemetryEvent(
            timestamp_ns=99, sensor_id="router-01", event_kind="packet_metadata",
            protocol="802.11", packet_length=80, channel_mhz=2412,
        )
        event = telemetry_to_sensor_event(source)
        self.assertEqual(event.modality, "wifi_telemetry")
        self.assertEqual(event.status, SensorEventStatus.CONTEXT)
        self.assertIsNone(event.evidence_score)


if __name__ == "__main__":
    unittest.main()
