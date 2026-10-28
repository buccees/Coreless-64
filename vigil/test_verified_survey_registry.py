"""Tests for the server-owned verified survey registry."""
import tempfile
import unittest
from pathlib import Path

from vigil.verified_survey_registry import VerifiedSurveyRegistry


class VerifiedSurveyRegistryTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = Path(self.tempdir.name) / "verified-surveys.sqlite3"
        self.registry = VerifiedSurveyRegistry(self.path)

    def tearDown(self):
        self.registry.close()
        self.tempdir.cleanup()

    def record(self, **overrides):
        values = {
            "crew_id": "crew-alpha",
            "world_seed": "PELAGOS-01",
            "artifact_id": "PEL-ARCHIVE-EXPEDITION-HANDBOOK",
            "site_id": "PEL-PRIVATEERS-HOLD",
            "survey_id": "survey-001",
            "unit_id": "UUV-01",
            "sensor_status": "accepted",
            "status": "CONFIRMED",
        }
        values.update(overrides)
        return self.registry.record_confirmed_survey(**values)

    def test_resolves_only_exact_crew_world_and_artifact(self):
        self.record()
        self.assertEqual(
            self.registry.resolve_verified_survey(
                "crew-alpha", "PELAGOS-01", "PEL-ARCHIVE-EXPEDITION-HANDBOOK"
            )["survey_id"],
            "survey-001",
        )
        self.assertIsNone(self.registry.resolve_verified_survey(
            "crew-bravo", "PELAGOS-01", "PEL-ARCHIVE-EXPEDITION-HANDBOOK"
        ))
        self.assertIsNone(self.registry.resolve_verified_survey(
            "crew-alpha", "PELAGOS-02", "PEL-ARCHIVE-EXPEDITION-HANDBOOK"
        ))
        self.assertIsNone(self.registry.resolve_verified_survey(
            "crew-alpha", "PELAGOS-01", "OTHER-ARTIFACT"
        ))

    def test_rejects_unaccepted_or_unconfirmed_evidence(self):
        for field, value in (("sensor_status", "context"), ("status", "SONAR INDICATION")):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.record(**{field: value})

    def test_reused_survey_id_cannot_change_evidence(self):
        self.record()
        self.record()
        with self.assertRaisesRegex(ValueError, "different evidence"):
            self.record(unit_id="UUV-02")

    def test_records_survive_reopen(self):
        self.record()
        self.registry.close()
        self.registry = VerifiedSurveyRegistry(self.path)
        evidence = self.registry.resolve_verified_survey(
            "crew-alpha", "PELAGOS-01", "PEL-ARCHIVE-EXPEDITION-HANDBOOK"
        )
        self.assertEqual(evidence["unit_id"], "UUV-01")
        self.assertEqual(evidence["status"], "CONFIRMED")
        self.assertEqual(evidence["sensor_status"], "accepted")

    def test_optional_evidence_cannot_override_authoritative_fields(self):
        record = self.record(evidence={
            "unit_id": "CLIENT-FAKE",
            "status": "SONAR INDICATION",
            "raw_quality": "calibrated",
        })
        self.assertEqual(record["unit_id"], "UUV-01")
        self.assertEqual(record["status"], "CONFIRMED")
        self.assertEqual(record["raw_quality"], "calibrated")


if __name__ == "__main__":
    unittest.main()
