import copy
import csv
from pathlib import Path
import unittest

from irforge_analysis.paired_sequences import compare_sequences


def rows():
    return [{"regime": "heldout", "family": "drift", "sequence_seed": seed, "frame_index": frame,
             "method": method, "accepted": method == "crc_confidence", "error": True, "has_target": True}
            for seed in range(5) for frame in range(2) for method in ("crc_temporal", "crc_confidence")]


class SequencePairTests(unittest.TestCase):
    def analyze(self, data):
        return compare_sequences(data, frames_per_sequence=2, resamples=200)

    def test_cluster_count_not_frame_count_and_abstention_utility(self):
        result = self.analyze(rows())["regimes"]["heldout"]
        self.assertEqual(result["sequences"], 5)
        self.assertIsNone(result["methods"]["crc_temporal"]["conditional_error"])
        self.assertEqual(result["paired_difference"]["sequence_false_release"]["ci_high"], -1)
        self.assertEqual(result["methods"]["crc_temporal"]["correct_release_per_frame"], 0)

    def test_duplicate_missing_and_mismatched_labels_rejected(self):
        modified = copy.deepcopy(rows())
        modified[0]["error"] = False
        for data in (rows() + rows()[:1], rows()[1:], modified):
            with self.assertRaises(ValueError):
                self.analyze(data)

    def test_order_independence(self):
        self.assertEqual(self.analyze(rows()), self.analyze(rows()[::-1]))

    def test_matched_boundary_does_not_round_below_zero(self):
        root = Path(__file__).resolve().parents[1]
        with (root / "artifacts/confirmatory-h6/benchmark_h6.csv").open(newline="", encoding="utf-8") as handle:
            data = list(csv.DictReader(handle))
        report = compare_sequences(data)["regimes"]["matched"]
        self.assertEqual(report["paired_difference"]["sequence_false_release"]["ci_high"], 0.0)


if __name__ == "__main__":
    unittest.main()
