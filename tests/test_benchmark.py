import tempfile
import unittest
from pathlib import Path

from irforge_sim.benchmark import run_benchmark
from irforge_sim.validation import validate_artifact


class BenchmarkTests(unittest.TestCase):
    def test_quick_benchmark_has_disjoint_splits_and_valid_hashes(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "quick"
            result = run_benchmark(
                output,
                seeds_per_family=2,
                train_per_family=4,
                calibration_per_family=4,
                bootstrap_resamples=20,
                include_ablations=False,
            )
            self.assertEqual(result["manifest"]["row_count"], 5 * 2 * 6)
            self.assertTrue(all(seed < 1000 for _, seed in result["manifest"]["train_seeds"]))
            self.assertTrue(validate_artifact(output, quick=True)["integrity"])


if __name__ == "__main__":
    unittest.main()

