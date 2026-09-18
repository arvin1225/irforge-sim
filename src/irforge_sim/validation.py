"""Independent integrity and logical-consistency checks for published artifacts."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np

from .benchmark import PRIMARY_MODES, evaluate_sample, fit_system
from .config import CONFIRMATORY_FAMILIES
from .image_formation import generate_sample


# The classical image pipeline is bitwise deterministic. The learned selective
# gate is refit during validation, and liblinear can differ at the last few
# decimal places across supported scikit-learn/BLAS builds. This tolerance is
# tight enough to detect a changed model while keeping the public artifact
# portable across the dependency ranges declared in pyproject.toml.
ROW_REPLAY_ATOL = 1e-6


def validate_artifact(artifact_dir: str | Path, *, quick: bool = False) -> dict[str, object]:
    root = Path(artifact_dir)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))
    with (root / "benchmark.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    checks: dict[str, bool] = {}
    checks["benchmark_hash"] = hashlib.sha256((root / "benchmark.csv").read_bytes()).hexdigest() == manifest["benchmark_sha256"]
    checks["summary_hash"] = hashlib.sha256((root / "summary.json").read_bytes()).hexdigest() == manifest["summary_sha256"]
    checks["row_count"] = len(rows) == int(manifest["row_count"])
    seed_start = int(manifest["confirmatory_seed_start"])
    checks["confirmatory_seeds"] = all(seed_start <= int(row["seed"]) < seed_start + int(manifest["seeds_per_family"]) for row in rows)
    checks["registered_families"] = set(row["family"] for row in rows) == set(CONFIRMATORY_FAMILIES)
    checks["primary_modes_present"] = set(PRIMARY_MODES).issubset(set(row["mode"] for row in rows))
    checks["fit_seeds_disjoint"] = all(int(seed) < 1000 for _, seed in manifest["train_seeds"] + manifest["calibration_seeds"])
    checks["finite_metrics"] = all(np.isfinite(float(value)) for mode in PRIMARY_MODES for value in summary["overall"][mode].values() if isinstance(value, (int, float)))
    checks["coverage_bounds"] = all(0.0 <= float(summary["overall"][mode]["coverage"]) <= 1.0 for mode in PRIMARY_MODES)

    sample_a = generate_sample(1003, "triple_shift")
    sample_b = generate_sample(1003, "triple_shift")
    checks["image_replay_exact"] = bool(np.array_equal(sample_a.image, sample_b.image) and np.array_equal(sample_a.target_mask, sample_b.target_mask))
    zero = generate_sample(1002, "attenuation_contrast", has_target=True, force_zero_contrast=True)
    checks["zero_contrast_control"] = zero.latent_contrast == 0.0

    if not quick:
        system = fit_system()
        replay_keys = [("blur_noise", seed_start), ("badpixel_fpn", seed_start + 3), ("triple_shift", seed_start + 6)]
        index = {(row["family"], int(row["seed"]), row["mode"]): row for row in rows}
        replay_ok = True
        for family, seed in replay_keys:
            for replay in evaluate_sample(system, generate_sample(seed, family), include_ablations=False):
                stored = index[(family, seed, replay["mode"])]
                replay_ok &= stored["accepted"].lower() == str(replay["accepted"]).lower()
                replay_ok &= abs(float(stored["confidence"]) - float(replay["confidence"])) <= ROW_REPLAY_ATOL
                replay_ok &= abs(float(stored["risk_score"]) - float(replay["risk_score"])) <= ROW_REPLAY_ATOL
                replay_ok &= stored["error"].lower() == str(replay["error"]).lower()
        checks["row_replay_within_1e-6"] = bool(replay_ok)

    report = {
        "integrity": all(checks.values()),
        "registered_success": bool(summary["registered_success"]),
        "checks": checks,
        "manifest": manifest,
    }
    (root / "validation-report.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report
