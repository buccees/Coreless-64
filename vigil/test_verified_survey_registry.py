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

    def simulation_inputs(self, **event_overrides):
        from vigil.historical_artifact_catalog import build_artifact_catalog
        artifact = build_artifact_catalog()[0]
        event = {
            "world_seed": "PELAGOS-01",
            "artifact_id": artifact["id"],
            "site_id": artifact["siteId"],
            "survey_id": "sim-survey-001",
            "unit_id": "UUV-01",
            "status": "CONFIRMED",
            "sensor_status": "accepted",
        }
        event.update(event_overrides)
        unit = {
            "id": "UUV-01", "crewId": "crew-alpha",
            "unitType": "submersible", "afloat": True,
            "x": artifact["x"], "y": artifact["y"],
        }
        return artifact, event, unit

    def test_simulation_ingestion_validates_canonical_site_and_authoritative_unit(self):
        artifact, event, unit = self.simulation_inputs()
        record = self.registry.record_from_simulation(
            crew_id="crew-alpha", world_seed="PELAGOS-01",
            artifact_id=artifact["id"], survey_event=event, unit_state=unit,
        )
        self.assertEqual(record["site_id"], artifact["siteId"])
        self.assertEqual(record["unit_id"], "UUV-01")
        self.assertEqual(
            self.registry.resolve_verified_survey(
                "crew-alpha", "PELAGOS-01", artifact["id"]
            )["survey_id"],
            "sim-survey-001",
        )

    def test_simulation_ingestion_rejects_mismatched_or_untrusted_events(self):
        cases = [
            ({"site_id": "FAKE-SITE"}, {}),
            ({"status": "SONAR INDICATION"}, {}),
            ({"sensor_status": "context"}, {}),
            ({"unit_id": "CLIENT-UNIT"}, {}),
            ({}, {"crewId": "crew-bravo"}),
            ({}, {"unitType": "surface-ship"}),
            ({}, {"afloat": False}),
            ({}, {"x": 0.99, "y": 0.99}),
            ({}, {"x": float("nan")}),
        ]
        for event_changes, unit_changes in cases:
            artifact, event, unit = self.simulation_inputs(**event_changes)
            unit.update(unit_changes)
            with self.subTest(event_changes=event_changes, unit_changes=unit_changes):
                with self.assertRaises(ValueError):
                    self.registry.record_from_simulation(
                        crew_id="crew-alpha", world_seed="PELAGOS-01",
                        artifact_id=artifact["id"], survey_event=event, unit_state=unit,
                    )
                self.assertIsNone(self.registry.resolve_verified_survey(
                    "crew-alpha", "PELAGOS-01", artifact["id"]
                ))

    def test_optional_evidence_cannot_override_authoritative_fields(self):
        record = self.record(evidence={
            "unit_id": "CLIENT-FAKE",
            "status": "SONAR INDICATION",
            "raw_quality": "calibrated",
        })
        self.assertEqual(record["unit_id"], "UUV-01")
        self.assertEqual(record["status"], "CONFIRMED")
        self.assertEqual(record["raw_quality"], "calibrated")


    def test_coreless_sensor_observation_can_enter_verified_registry(self):
        from vigil.model import Observation, Provenance, SensorState
        artifact, event, unit = self.simulation_inputs()
        observation = Observation(
            observation_id="obs-001",
            source_id="sonar-UUV-01",
            timestamp_ns=100,
            payload={
                "survey_id": event["survey_id"],
                "world_seed": event["world_seed"],
                "artifact_id": event["artifact_id"],
                "site_id": event["site_id"],
                "unit_id": event["unit_id"],
                "status": event["status"],
                "sensor_status": event["sensor_status"],
            },
            confidence=0.95,
            provenance=Provenance(
                source_id="sonar-UUV-01",
                source_type="sonar",
                created_ns=100,
            ),
            sensor_state=SensorState.HEALTHY,
        )
        result = self.registry.record_observation_from_simulation(
            crew_id="crew-alpha",
            world_seed="PELAGOS-01",
            artifact_id=artifact["id"],
            observation=observation,
            unit_state=unit,
        )
        self.assertEqual(result["survey_id"], "sim-survey-001")
        self.assertEqual(
            self.registry.resolve_verified_survey(
                "crew-alpha", "PELAGOS-01", artifact["id"]
            )["unit_id"],
            "UUV-01",
        )

    def test_coreless_sensor_bridge_rejects_degraded_low_confidence_or_missing_provenance(self):
        from vigil.model import Observation, Provenance, SensorState
        artifact, event, unit = self.simulation_inputs()
        payload = dict(event)
        valid_provenance = Provenance(
            source_id="sonar-UUV-01", source_type="sonar", created_ns=100
        )
        cases = [
            {"sensor_state": SensorState.DEGRADED, "confidence": 0.99,
             "provenance": valid_provenance},
            {"sensor_state": SensorState.HEALTHY, "confidence": 0.5,
             "provenance": valid_provenance},
            {"sensor_state": SensorState.HEALTHY, "confidence": 0.99,
             "provenance": None},
        ]
        for index, options in enumerate(cases):
            observation = Observation(
                observation_id=f"obs-bad-{index}",
                source_id="sonar-UUV-01",
                timestamp_ns=100,
                payload=payload,
                **options,
            )
            with self.subTest(index=index), self.assertRaises(ValueError):
                self.registry.record_observation_from_simulation(
                    crew_id="crew-alpha",
                    world_seed="PELAGOS-01",
                    artifact_id=artifact["id"],
                    observation=observation,
                    unit_state=unit,
                )
        self.assertIsNone(self.registry.resolve_verified_survey(
            "crew-alpha", "PELAGOS-01", artifact["id"]
        ))

if __name__ == "__main__":
    unittest.main()
