import unittest

import numpy as np

from irforge_sim.detectors import LearnedPixelDetector, evaluate_score_map, local_contrast_map, tune_threshold
from irforge_sim.image_formation import generate_sample


class DetectorTests(unittest.TestCase):
    def test_local_contrast_map_is_bounded(self):
        sample = generate_sample(2, "nominal")
        score = local_contrast_map(sample.image)
        self.assertEqual(score.shape, sample.image.shape)
        self.assertGreaterEqual(float(score.min()), 0.0)
        self.assertLessEqual(float(score.max()), 1.0)

    def test_learned_detector_is_deterministic(self):
        samples = [generate_sample(seed, "nominal") for seed in range(8)]
        first = LearnedPixelDetector().fit(samples)
        second = LearnedPixelDetector().fit(samples)
        self.assertTrue(np.allclose(first.predict_map(samples[0].image), second.predict_map(samples[0].image)))

    def test_threshold_comes_from_candidate_grid(self):
        samples = [generate_sample(seed, "nominal") for seed in range(10)]
        maps = [local_contrast_map(sample.image) for sample in samples]
        threshold = tune_threshold(samples, maps)
        self.assertGreaterEqual(threshold, 0.25)
        self.assertLessEqual(threshold, 0.9995)
        result = evaluate_score_map(samples[0], maps[0], threshold)
        self.assertIsInstance(result.correct, bool)


if __name__ == "__main__":
    unittest.main()
