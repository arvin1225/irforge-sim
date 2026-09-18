from __future__ import annotations

import unittest
from pathlib import Path

from irforge_sim.validation_v2 import validate_h6_artifact


ROOT = Path(__file__).resolve().parents[1]


class H6ArtifactTests(unittest.TestCase):
    def test_published_h6_artifact_passes_integrity_not_success(self) -> None:
        report = validate_h6_artifact(ROOT / "artifacts" / "confirmatory-h6")
        self.assertTrue(report["integrity"], report["checks"])
        self.assertFalse(report["registered_success"])


if __name__ == "__main__":
    unittest.main()

