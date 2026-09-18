import unittest

import numpy as np

from irforge_sim.image_formation import band_radiance, generate_sample


class ImageFormationTests(unittest.TestCase):
    def test_planck_band_radiance_increases_with_temperature(self):
        self.assertGreater(band_radiance(305.0), band_radiance(285.0))

    def test_sample_replay_is_exact(self):
        first = generate_sample(1004, "triple_shift")
        second = generate_sample(1004, "triple_shift")
        self.assertTrue(np.array_equal(first.image, second.image))
        self.assertEqual(first.config, second.config)

    def test_composed_families_change_multiple_axes(self):
        blur_noise = generate_sample(1000, "blur_noise").config
        self.assertGreater(blur_noise.blur_sigma, 1.0)
        self.assertGreater(blur_noise.read_noise, 0.03)
        bad_fpn = generate_sample(1000, "badpixel_fpn").config
        self.assertGreater(bad_fpn.bad_pixel_fraction, 0.01)
        self.assertGreater(bad_fpn.fpn_gain, 0.02)

    def test_zero_contrast_negative_control(self):
        sample = generate_sample(7, "nominal", has_target=True, force_zero_contrast=True)
        self.assertEqual(sample.latent_contrast, 0.0)
        self.assertTrue(sample.has_target)


if __name__ == "__main__":
    unittest.main()

