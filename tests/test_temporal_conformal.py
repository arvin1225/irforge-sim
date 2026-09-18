from __future__ import annotations

import unittest

import numpy as np

from irforge_sim.conformal import sequence_crc_threshold
from irforge_sim.temporal import generate_sequence, temporal_residual_maps


class TemporalConformalTests(unittest.TestCase):
    def test_sequence_replay_is_exact(self) -> None:
        first = generate_sequence(3001, "compound_aging")
        second = generate_sequence(3001, "compound_aging")
        self.assertEqual(len(first.frames), 12)
        for left, right in zip(first.frames, second.frames, strict=True):
            self.assertTrue(np.array_equal(left.image, right.image))
            self.assertEqual(left.target_xy, right.target_xy)

    def test_drift_changes_observable_frames(self) -> None:
        sequence = generate_sequence(3000, "gain_ramp")
        self.assertGreater(float(np.mean(np.abs(sequence.frames[-1].image - sequence.frames[0].image))), 0.01)
        self.assertGreater(sequence.drift_magnitudes[-1], sequence.drift_magnitudes[0])

    def test_temporal_residual_is_causal_and_complete(self) -> None:
        sequence = generate_sequence(3000, "blur_creep")
        maps = temporal_residual_maps(sequence)
        self.assertEqual(len(maps), len(sequence.frames))
        self.assertTrue(all(score.shape == sequence.frames[0].image.shape for score in maps))
        self.assertTrue(all(np.all(np.isfinite(score)) for score in maps))

    def test_crc_uses_sequence_level_bounded_loss(self) -> None:
        risks = [np.array([0.1, 0.4]), np.array([0.2, 0.5]), np.array([0.3, 0.6])] * 10
        errors = [np.array([False, True]), np.array([False, False]), np.array([False, True])] * 10
        result = sequence_crc_threshold(risks, errors, alpha=0.10)
        self.assertLessEqual(result.corrected_risk, 0.10 + 1e-12)
        self.assertEqual(result.sequence_count, 30)


if __name__ == "__main__":
    unittest.main()

