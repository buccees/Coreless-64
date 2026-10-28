"""Regression tests for the stable Pelagos historical-artifact spawn catalog."""
import unittest

from vigil.historical_artifact_catalog import ARTIFACT_CATALOG, build_artifact_catalog


class HistoricalArtifactCatalogTests(unittest.TestCase):
    def test_catalog_has_six_unique_non_respawning_identity_slots(self):
        catalog = build_artifact_catalog()
        ids = [item["id"] for item in catalog]
        sites = [item["siteId"] for item in catalog]
        self.assertEqual(len(catalog), 6)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(sites), len(set(sites)))
        self.assertEqual(len(ARTIFACT_CATALOG), 6)

    def test_coordinates_are_stable_grid_cell_centers(self):
        first = build_artifact_catalog()
        second = build_artifact_catalog()
        self.assertEqual(first, second)
        for item, source in zip(first, ARTIFACT_CATALOG):
            self.assertEqual(item["x"], (source["gridX"] + 0.5) / 42)
            self.assertEqual(item["y"], (source["gridY"] + 0.5) / 42)
            self.assertGreaterEqual(item["x"], 0)
            self.assertLessEqual(item["x"], 1)
            self.assertGreaterEqual(item["y"], 0)
            self.assertLessEqual(item["y"], 1)

    def test_catalog_builder_returns_independent_records(self):
        first = build_artifact_catalog()
        first[0]["id"] = "MUTATED"
        self.assertNotEqual(build_artifact_catalog()[0]["id"], "MUTATED")


if __name__ == "__main__":
    unittest.main()
