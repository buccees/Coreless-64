"""Static contract checks for the Control Room's optional live feed."""
from pathlib import Path
import unittest


class SensorFeedContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (Path(__file__).resolve().parents[1] / "index.html").read_text(encoding="utf-8")

    def test_polling_is_opt_in_and_periodic(self):
        self.assertIn("feedPollMs = 3000", self.html)
        self.assertIn("feedTimer = window.setInterval(pollFeed, feedPollMs)", self.html)
        self.assertIn("feedConnect.addEventListener('click'", self.html)

    def test_disconnect_stops_polling_and_aborts_request(self):
        self.assertIn("function stopFeedTimer()", self.html)
        self.assertIn("stopFeedTimer();", self.html)
        self.assertIn("if (feedAbort) feedAbort.abort();", self.html)
        self.assertIn("feedBaseUrl = null;", self.html)

    def test_refresh_failure_exposes_stale_state(self):
        self.assertIn("FEED STALE · RETRYING", self.html)
        self.assertIn("Last successful update:", self.html)
        self.assertIn("row.freshness", self.html)
        self.assertIn("row.age_ns", self.html)

    def test_reconnect_ignores_responses_from_previous_connection(self):
        self.assertIn("var feedConnectionGeneration = 0", self.html)
        self.assertIn("feedConnectionGeneration++;", self.html)
        self.assertIn("requestGeneration !== feedConnectionGeneration", self.html)
        self.assertIn("if (requestGeneration === feedConnectionGeneration) feedRequestActive = false", self.html)

    def test_last_successful_events_remain_available_on_refresh_failure(self):
        failure_start = self.html.index("feedState.textContent = feedFailureCount >= 2 ? 'FEED STALE")
        failure_end = self.html.index("}).finally(function()", failure_start)
        failure_path = self.html[failure_start:failure_end]
        self.assertNotIn("feedEvents.hidden = true", failure_path)
        self.assertIn("Last successful update:", failure_path)

    def test_demo_and_live_feed_are_not_conflated(self):
        self.assertIn("SYNTHETIC DATASET · NOT LIVE", self.html)
        self.assertIn("does not verify physical sensor connectivity", self.html)
        self.assertIn("credentials: 'omit'", self.html)


if __name__ == "__main__":
    unittest.main()
