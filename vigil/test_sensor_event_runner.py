"""Tests for the explicit-input CSI event-feed runner."""
import json
import tempfile
import unittest
from pathlib import Path

from vigil.sensor_event import SensorEventLedger, SensorEventStatus
from vigil.sensor_event_runner import _complex_vector, load_csi_jsonl


class SensorEventRunnerTests(unittest.TestCase):
    def test_complex_vector_accepts_real_and_complex_pairs(self):
        self.assertEqual(_complex_vector([1, [2, -3]], "v"), (1 + 0j, 2 - 3j))

    def test_loads_samples_through_csi_pipeline_as_context(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "samples.jsonl"
            rows = [
                {"timestamp_ns": 10, "sensor_id": "csi-1", "channel_mhz": 2412,
                 "baseline": [[1, 0], [1, 0]], "current": [[1, 0], [1, 0]]},
                {"timestamp_ns": 20, "sensor_id": "csi-1", "channel_mhz": 2412,
                 "baseline": [[1, 0], [1, 0]], "current": [[1.4, 0.2], [0.8, -0.1]],
                 "signal_dbm": -48.0},
            ]
            path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
            ledger = SensorEventLedger()
            self.assertEqual(load_csi_jsonl(path, ledger), 2)
            events = ledger.snapshot(now_ns=20, limit=10)
            self.assertEqual(len(events), 2)
            self.assertEqual(events[0].timestamp_ns, 20)
            self.assertEqual(events[0].status, SensorEventStatus.CONTEXT)
            self.assertIsNone(events[0].confidence)
            self.assertIn("not a position fix", events[0].reason)

    def test_invalid_row_reports_line_number(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.jsonl"
            path.write_text('{"timestamp_ns": 1}\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, r":1: sensor_id"):
                load_csi_jsonl(path, SensorEventLedger())


if __name__ == "__main__":
    unittest.main()
