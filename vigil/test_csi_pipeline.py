"""Tests for the CSI-to-telemetry processing pipeline."""
import unittest

from vigil.rf_csi import MotionEvidenceFilter
from vigil.telemetry_store import TelemetryStore
from vigil.csi_pipeline import CsiTelemetryPipeline


class CsiPipelineTests(unittest.TestCase):
    def setUp(self):
        self.store = TelemetryStore()
        self.pipeline = CsiTelemetryPipeline(
            sensor_id="wifi-csi-1", channel_mhz=2437, store=self.store,
            motion_filter=MotionEvidenceFilter(alpha=1, high_threshold=.2,
                                               low_threshold=.1, enter_samples=1),
        )

    def tearDown(self):
        self.store.close()

    def test_processes_and_persists_motion_evidence(self):
        result = self.pipeline.process(
            timestamp_ns=100, baseline=[1+0j, 2+0j],
            current=[1.5+0j, 3+0j], packet_length=128, signal_dbm=-48.0,
        )
        self.assertEqual(result.sensor_id, "wifi-csi-1")
        self.assertTrue(result.motion.active)
        row = self.store.recent()[0]
        self.assertEqual(row["event_kind"], "csi_motion_evidence")
        self.assertEqual(row["channel_mhz"], 2437)
        self.assertAlmostEqual(row["motion_evidence"], result.motion.smoothed_evidence)

    def test_quiet_sample_is_recorded(self):
        result = self.pipeline.process(
            timestamp_ns=100, baseline=[1+0j, 2+0j], current=[1+0j, 2+0j],
        )
        self.assertFalse(result.motion.active)
        self.assertEqual(len(self.store.recent()), 1)

    def test_rejects_out_of_order_timestamp_without_recording(self):
        self.pipeline.process(timestamp_ns=100, baseline=[1+0j], current=[1.2+0j])
        with self.assertRaises(ValueError):
            self.pipeline.process(timestamp_ns=100, baseline=[1+0j], current=[1.2+0j])
        self.assertEqual(len(self.store.recent()), 1)

    def test_rejects_bad_signal_metadata(self):
        with self.assertRaises(ValueError):
            self.pipeline.process(timestamp_ns=100, baseline=[1+0j], current=[1+0j],
                                  signal_dbm=float("nan"))


if __name__ == "__main__":
    unittest.main()
