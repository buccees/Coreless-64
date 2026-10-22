"""Tests for the read-only local sensor event feed."""
import json
import threading
import unittest
from http.server import HTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from vigil.sensor_event import SensorEventLedger, SensorEventRecord, SensorEventStatus
from vigil.sensor_event_api import make_sensor_event_handler


class SensorEventApiTests(unittest.TestCase):
    def setUp(self):
        self.ledger = SensorEventLedger()
        self.ledger.append(SensorEventRecord(
            event_id="evt-1", sensor_id="wifi-demo", timestamp_ns=900,
            modality="wifi_csi", event_kind="csi_motion_evidence",
            status=SensorEventStatus.CONTEXT,
            reason="CSI motion context only; not a position fix.",
            evidence_score=0.4, calibration_status="environment_calibration_required",
        ))
        handler = make_sensor_event_handler(self.ledger, clock_ns=lambda: 1000)
        self.server = HTTPServer(("127.0.0.1", 0), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def test_events_are_json_with_freshness_and_evidence_semantics(self):
        with urlopen(self.base + "/events?max_age_ns=200") as response:
            data = json.loads(response.read())
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["events"][0]["freshness"], "current")
        self.assertEqual(data["events"][0]["evidence_score"], 0.4)
        self.assertEqual(data["events"][0]["status"], "context")

    def test_health_does_not_claim_hardware_connected(self):
        with urlopen(self.base + "/health") as response:
            data = json.loads(response.read())
        self.assertFalse(data["hardware_connected"])

    def test_post_is_not_allowed(self):
        request = Request(self.base + "/events", data=b"{}", method="POST")
        with self.assertRaises(HTTPError) as raised:
            urlopen(request)
        self.assertEqual(raised.exception.code, 405)

    def test_invalid_limit_is_rejected(self):
        with self.assertRaises(HTTPError) as raised:
            urlopen(self.base + "/events?limit=0")
        self.assertEqual(raised.exception.code, 400)


if __name__ == "__main__":
    unittest.main()
