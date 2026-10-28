"""Tests for survey-verified, fail-closed artifact discovery authorization."""
import unittest

from vigil.historical_artifact_authority import make_artifact_discovery_authorizer
from vigil.historical_artifact_catalog import build_artifact_catalog


class ArtifactDiscoveryAuthorityTests(unittest.TestCase):
    def setUp(self):
        artifact = build_artifact_catalog()[0]
        self.artifact = artifact
        self.unit = {
            "id": "UUV-01", "crewId": "crew-alpha",
            "unitType": "submersible", "afloat": True,
            "x": artifact["x"], "y": artifact["y"],
        }
        self.evidence = {
            "survey_id": "survey-verified-001",
            "world_seed": "PELAGOS-01",
            "artifact_id": artifact["id"],
            "site_id": artifact["siteId"],
            "unit_id": "UUV-01",
            "status": "CONFIRMED",
            "sensor_status": "accepted",
        }

    def authorize(self, evidence=None, unit=None, *, wired=True):
        evidence = self.evidence if evidence is None else evidence
        unit = self.unit if unit is None else unit
        return make_artifact_discovery_authorizer(
            resolve_unit=(lambda unit_id: unit) if wired else None,
            resolve_verified_survey=(lambda crew, seed, artifact_id: evidence) if wired else None,
        )("crew-alpha", "PELAGOS-01", self.artifact["id"])

    def test_accepts_server_verified_survey_at_catalogued_site(self):
        self.assertTrue(self.authorize())

    def test_fails_closed_when_simulation_callbacks_are_not_wired(self):
        self.assertFalse(self.authorize(wired=False))

    def test_rejects_client_like_unconfirmed_or_unaccepted_evidence(self):
        for field, value in (("status", "SONAR INDICATION"), ("sensor_status", "context")):
            evidence = dict(self.evidence, **{field: value})
            with self.subTest(field=field):
                self.assertFalse(self.authorize(evidence=evidence))

    def test_rejects_wrong_site_world_artifact_or_missing_survey_id(self):
        for field, value in (("site_id", "OTHER-SITE"),
                             ("world_seed", "OTHER-WORLD"),
                             ("artifact_id", "OTHER-ARTIFACT"),
                             ("survey_id", "")):
            evidence = dict(self.evidence, **{field: value})
            with self.subTest(field=field):
                self.assertFalse(self.authorize(evidence=evidence))

    def test_rejects_unowned_inactive_or_distant_submersible(self):
        cases = [
            dict(self.unit, crewId="crew-bravo"),
            dict(self.unit, afloat=False),
            dict(self.unit, x=0.9, y=0.9),
            dict(self.unit, x=float("nan")),
        ]
        for unit in cases:
            with self.subTest(unit=unit):
                self.assertFalse(self.authorize(unit=unit))

    def test_rejects_unknown_artifact_id(self):
        authorizer = make_artifact_discovery_authorizer(
            resolve_unit=lambda unit_id: self.unit,
            resolve_verified_survey=lambda crew, seed, artifact_id: self.evidence,
        )
        self.assertFalse(authorizer("crew-alpha", "PELAGOS-01", "NOT-IN-CATALOG"))


if __name__ == "__main__":
    unittest.main()
