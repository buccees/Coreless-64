"""Tests for Wi-Fi CSI feature extraction and temporal filtering."""
import math
import unittest

from vigil.rf_csi import MotionEvidenceFilter, extract_csi_features


class CsiFeatureTests(unittest.TestCase):
    def test_identical_samples_have_no_change_evidence(self):
        samples = [complex(1, 0), complex(0, 2), complex(-1, 1)]
        features = extract_csi_features(samples, samples)
        self.assertEqual(features.subcarrier_count, 3)
        self.assertAlmostEqual(features.amplitude_rms_delta, 0)
        self.assertAlmostEqual(features.phase_rms_delta_rad, 0)
        self.assertAlmostEqual(features.motion_evidence, 0)

    def test_amplitude_change_increases_evidence(self):
        baseline = [complex(1, 0), complex(2, 0)]
        current = [complex(1.5, 0), complex(3, 0)]
        features = extract_csi_features(baseline, current)
        self.assertAlmostEqual(features.amplitude_rms_delta, 0.5)
        self.assertGreater(features.motion_evidence, 0)

    def test_phase_wrap_uses_shortest_delta(self):
        baseline = [complex(math.cos(math.pi - .01), math.sin(math.pi - .01))]
        current = [complex(math.cos(-math.pi + .01), math.sin(-math.pi + .01))]
        features = extract_csi_features(baseline, current)
        self.assertAlmostEqual(features.phase_rms_delta_rad, .02, places=6)

    def test_misaligned_vectors_rejected(self):
        with self.assertRaises(ValueError):
            extract_csi_features([1+0j], [1+0j, 2+0j])

    def test_zero_and_nonfinite_samples_rejected(self):
        with self.assertRaises(ValueError):
            extract_csi_features([1+0j], [0j])
        with self.assertRaises(ValueError):
            extract_csi_features([complex(float("nan"), 0)], [1+0j])

    def test_filter_requires_sustained_motion_to_enter(self):
        f = MotionEvidenceFilter(alpha=1, high_threshold=.5, low_threshold=.2, enter_samples=2)
        self.assertFalse(f.update(.8).active)
        self.assertTrue(f.update(.8).active)

    def test_filter_hysteresis_prevents_immediate_exit(self):
        f = MotionEvidenceFilter(alpha=1, high_threshold=.5, low_threshold=.2, enter_samples=1, exit_samples=2)
        self.assertTrue(f.update(.8).active)
        self.assertTrue(f.update(.1).active)
        self.assertFalse(f.update(.1).active)

    def test_filter_rejects_invalid_evidence(self):
        f = MotionEvidenceFilter()
        for value in (-.1, 1.1, float("nan")):
            with self.assertRaises(ValueError):
                f.update(value)

    def test_filter_rejects_invalid_configuration(self):
        with self.assertRaises(ValueError):
            MotionEvidenceFilter(alpha=0)
        with self.assertRaises(ValueError):
            MotionEvidenceFilter(low_threshold=.5, high_threshold=.5)


if __name__ == "__main__":
    unittest.main()
