import unittest

import numpy as np

from irforge_sim.metrics import aurc, expected_calibration_error, paired_bootstrap_aurc, paired_bootstrap_fixed_coverage
from irforge_sim.selective import TemperatureCalibrator, acceptance_threshold


class SelectiveMetricTests(unittest.TestCase):
    def test_perfect_confidence_has_zero_ece(self):
        confidence = np.array([0.9, 0.8, 0.7, 0.6])
        correctness = confidence.copy()
        self.assertAlmostEqual(expected_calibration_error(confidence, correctness, bins=4), 0.0)

    def test_aurc_rewards_error_ranking(self):
        errors = np.array([0, 0, 1, 1])
        self.assertLess(aurc(errors, np.array([0.1, 0.2, 0.8, 0.9])), aurc(errors, np.array([0.9, 0.8, 0.2, 0.1])))

    def test_temperature_and_coverage_threshold_are_finite(self):
        calibrator = TemperatureCalibrator.fit(np.array([0.9, 0.8, 0.7, 0.6]), np.array([1, 1, 0, 0]))
        self.assertGreater(calibrator.temperature, 0.0)
        threshold = acceptance_threshold(np.arange(10) / 10.0, 0.8)
        self.assertTrue(np.isfinite(threshold))

    def test_fixed_coverage_comparison_is_paired(self):
        rows_a = [
            {"family": "x", "seed": index, "error": error, "risk_score": risk}
            for index, (error, risk) in enumerate([(0, 0.1), (0, 0.2), (1, 0.8), (1, 0.9)])
        ]
        rows_b = [
            {"family": "x", "seed": index, "error": error, "risk_score": risk}
            for index, (error, risk) in enumerate([(0, 0.9), (0, 0.8), (1, 0.2), (1, 0.1)])
        ]
        result = paired_bootstrap_fixed_coverage(rows_a, rows_b, coverage=0.5, resamples=30)
        self.assertLess(result["difference"], 0.0)

    def test_aurc_bootstrap_detects_better_ranking(self):
        rows_a = [
            {"family": "x", "seed": index, "error": error, "risk_score": risk}
            for index, (error, risk) in enumerate([(0, 0.1), (0, 0.2), (1, 0.8), (1, 0.9)])
        ]
        rows_b = [
            {"family": "x", "seed": index, "error": error, "risk_score": risk}
            for index, (error, risk) in enumerate([(0, 0.9), (0, 0.8), (1, 0.2), (1, 0.1)])
        ]
        result = paired_bootstrap_aurc(rows_a, rows_b, resamples=30)
        self.assertLess(result["difference"], 0.0)


if __name__ == "__main__":
    unittest.main()
