"""Regression tests for the authoritative historical artifact custody ledger."""
import threading
import unittest

from vigil.historical_artifact_store import HistoricalArtifactStore


CATALOG = [
    {"id": "ART-ONE", "siteId": "SITE-ONE", "x": 0.20, "y": 0.30},
    {"id": "ART-TWO", "siteId": "SITE-TWO", "x": 0.80, "y": 0.70},
]


def sub(unit_id, x, y, side="friendly", *, locked=True, afloat=True):
    return {
        "id": unit_id, "unitType": "submersible", "x": x, "y": y,
        "side": side, "afloat": afloat,
        "lockedArtifactContainer": {"locked": locked, "artifactIds": []},
    }


class HistoricalArtifactStoreTests(unittest.TestCase):
    def setUp(self):
        self.store = HistoricalArtifactStore(CATALOG)

    def tearDown(self):
        self.store.close()

    def test_catalogue_is_unique_and_seed_isolated(self):
        first = self.store.inventory("PELAGOS-01")
        again = self.store.inventory("PELAGOS-01")
        other_world = self.store.inventory("PELAGOS-02")
        self.assertEqual([x["id"] for x in first], ["ART-ONE", "ART-TWO"])
        self.assertEqual(len(again), 2)
        self.assertEqual(len(other_world), 2)
        self.assertTrue(all(x["unique"] and not x["respawnable"] for x in first))
        self.assertEqual(first[0]["status"], "AT_SITE")
        self.assertFalse(first[0]["discovered"])

    def test_discovery_is_idempotent_and_site_bound(self):
        self.store.discover("PELAGOS-01", "ART-ONE")
        self.store.discover("PELAGOS-01", "ART-ONE")
        self.assertEqual(len(self.store.events("PELAGOS-01", "ART-ONE")), 1)
        with self.assertRaisesRegex(ValueError, "catalogued recovery site"):
            self.store.discover("PELAGOS-01", "ART-ONE", "OTHER-SITE")

    def test_collection_requires_discovery_proximity_and_locked_container(self):
        with self.assertRaisesRegex(ValueError, "discovered"):
            self.store.collect("PELAGOS-01", "ART-ONE", "UUV-1", sub("UUV-1", .20, .30))
        self.store.discover("PELAGOS-01", "ART-ONE")
        with self.assertRaisesRegex(ValueError, "current coordinates"):
            self.store.collect("PELAGOS-01", "ART-ONE", "UUV-1", sub("UUV-1", .5, .5))
        with self.assertRaisesRegex(ValueError, "locked container"):
            self.store.collect("PELAGOS-01", "ART-ONE", "UUV-1", sub("UUV-1", .20, .30, locked=False))
        held = self.store.collect("PELAGOS-01", "ART-ONE", "UUV-1", sub("UUV-1", .20, .30))
        self.assertEqual(held["status"], "CARRIED")
        self.assertEqual(held["carrierId"], "UUV-1")
        with self.assertRaisesRegex(ValueError, "already in custody"):
            self.store.collect("PELAGOS-01", "ART-ONE", "UUV-2", sub("UUV-2", .20, .30))

    def test_loss_persists_coordinates_and_allows_recovery(self):
        self.store.discover("PELAGOS-01", "ART-ONE")
        self.store.collect("PELAGOS-01", "ART-ONE", "UUV-1", sub("UUV-1", .20, .30))
        lost = self.store.lose("PELAGOS-01", "ART-ONE", "UUV-1", sub("UUV-1", .25, .35))
        self.assertEqual(lost["status"], "LOST")
        self.assertEqual(lost["location"], {"x": .25, "y": .35})
        recovered = self.store.collect("PELAGOS-01", "ART-ONE", "UUV-2", sub("UUV-2", .25, .35))
        self.assertEqual(recovered["status"], "CARRIED")
        self.assertEqual(recovered["carrierId"], "UUV-2")
        self.assertEqual([e["action"] for e in self.store.events("PELAGOS-01", "ART-ONE")],
                         ["DISCOVER", "COLLECT", "LOSS", "COLLECT"])

    def test_confirmed_sinking_drops_artifact_at_last_known_track(self):
        self.store.discover("PELAGOS-01", "ART-ONE")
        self.store.collect("PELAGOS-01", "ART-ONE", "UUV-1", sub("UUV-1", .20, .30))
        with self.assertRaises(ValueError):
            self.store.drop_on_sinking("PELAGOS-01", "ART-ONE", "UUV-1", last_known_x=.24, last_known_y=.31, sink_event_authorized=False)
        dropped = self.store.drop_on_sinking("PELAGOS-01", "ART-ONE", "UUV-1", last_known_x=.24, last_known_y=.31, sink_event_authorized=True)
        self.assertEqual(dropped["status"], "LOST")
        self.assertEqual(dropped["location"], {"x": .24, "y": .31})
        self.assertEqual(dropped["carrierId"], "")

    def test_transfer_and_capture_require_proximity_and_faction_rules(self):
        self.store.discover("PELAGOS-01", "ART-ONE")
        self.store.collect("PELAGOS-01", "ART-ONE", "UUV-1", sub("UUV-1", .20, .30))
        with self.assertRaisesRegex(ValueError, "opposing factions"):
            self.store.transfer("PELAGOS-01", "ART-ONE", "UUV-1", "UUV-2",
                                sub("UUV-1", .20, .30), sub("UUV-2", .21, .30), capture=True)
        with self.assertRaisesRegex(ValueError, "opposing factions"):
            self.store.transfer("PELAGOS-01", "ART-ONE", "UUV-1", "UUV-2",
                                sub("UUV-1", .20, .30), sub("UUV-2", .21, .30), capture=False)
        captured = self.store.transfer("PELAGOS-01", "ART-ONE", "UUV-1", "UUV-2",
                                       sub("UUV-1", .20, .30), sub("UUV-2", .21, .30, "hostile"),
                                       capture=True)
        self.assertEqual(captured["carrierId"], "UUV-2")
        self.assertEqual(self.store.events("PELAGOS-01", "ART-ONE")[-1]["action"], "CAPTURE")

    def test_concurrent_collection_has_one_winner(self):
        self.store.discover("PELAGOS-01", "ART-ONE")
        barrier = threading.Barrier(2)
        outcomes = []

        def attempt(unit_id):
            barrier.wait()
            try:
                outcomes.append(self.store.collect("PELAGOS-01", "ART-ONE", unit_id,
                                                   sub(unit_id, .20, .30))["carrierId"])
            except ValueError:
                outcomes.append("DENIED")

        threads = [threading.Thread(target=attempt, args=(uid,)) for uid in ("UUV-1", "UUV-2")]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(sum(value != "DENIED" for value in outcomes), 1)
        self.assertEqual(self.store.inventory("PELAGOS-01")[0]["status"], "CARRIED")

    def test_untrusted_or_invalid_unit_state_is_rejected(self):
        self.store.discover("PELAGOS-01", "ART-ONE")
        with self.assertRaisesRegex(ValueError, "authoritative server"):
            self.store.collect("PELAGOS-01", "ART-ONE", "UUV-1", sub("SOMEONE-ELSE", .20, .30))
        with self.assertRaisesRegex(ValueError, "active submersible"):
            self.store.collect("PELAGOS-01", "ART-ONE", "UUV-1",
                               sub("UUV-1", .20, .30, afloat=False))


if __name__ == "__main__":
    unittest.main()
