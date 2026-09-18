import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PublishedArtifactTests(unittest.TestCase):
    def test_dashboard_preserves_negative_replication_decision(self) -> None:
        dashboard = json.loads((ROOT / "web" / "public" / "data" / "benchmark.json").read_text(encoding="utf-8"))
        frozen = json.loads((ROOT / "artifacts" / "replication-h5" / "replication-summary.json").read_text(encoding="utf-8"))
        self.assertFalse(dashboard["replicationDecision"]["H5_pass"])
        self.assertEqual(dashboard["replicationDecision"]["H5_pass"], frozen["H5_pass"])
        self.assertAlmostEqual(dashboard["replicationDecision"]["relative_aurc_reduction"], frozen["relative_aurc_reduction"])

    def test_dashboard_curves_and_exact_sample_images_exist(self) -> None:
        dashboard = json.loads((ROOT / "web" / "public" / "data" / "benchmark.json").read_text(encoding="utf-8"))
        for study in ("confirmation", "replication"):
            self.assertEqual(set(dashboard["studies"][study]["risk"]), {"confidence_selective", "shift_selective", "quality_selective"})
            for values in dashboard["studies"][study]["risk"].values():
                self.assertEqual(len(values["curve"]), 81)
                self.assertTrue(0.0 <= values["aurc"] <= 1.0)
        self.assertGreaterEqual(len(dashboard["samples"]), 5)
        for sample in dashboard["samples"]:
            path = ROOT / "web" / "public" / sample["image"].removeprefix("/")
            self.assertTrue(path.is_file(), path)
            self.assertEqual(path.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")

    def test_publication_figures_include_vector_and_raster_exports(self) -> None:
        for stem in ("fig_failure_atlas", "fig_sensor_shift_gallery"):
            png = ROOT / "figures" / f"{stem}.png"
            pdf = ROOT / "figures" / f"{stem}.pdf"
            self.assertEqual(png.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
            self.assertTrue(pdf.read_bytes().startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
