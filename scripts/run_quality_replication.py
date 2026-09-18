from __future__ import annotations

import json
import hashlib
from pathlib import Path

from irforge_sim.benchmark import run_benchmark
from irforge_sim.metrics import paired_bootstrap_aurc, paired_bootstrap_fixed_coverage, summarize_rows


def main() -> int:
    output = Path("artifacts/replication-h5")
    result = run_benchmark(
        output,
        confirm_seed_start=2000,
        seeds_per_family=80,
        train_per_family=24,
        calibration_per_family=16,
        bootstrap_resamples=5000,
        include_ablations=True,
    )
    quality = [row for row in result["rows"] if row["mode"] == "quality_selective"]
    confidence = [row for row in result["rows"] if row["mode"] == "confidence_selective"]
    quality_summary = summarize_rows(quality)
    confidence_summary = summarize_rows(confidence)
    bootstrap = paired_bootstrap_aurc(quality, confidence, resamples=5000)
    fixed_coverage = paired_bootstrap_fixed_coverage(quality, confidence, coverage=0.8, resamples=5000)
    relative_reduction = (
        float(confidence_summary["aurc"]) - float(quality_summary["aurc"])
    ) / max(float(confidence_summary["aurc"]), 1e-9)
    summary = {
        "H5_pass": relative_reduction >= 0.10 and bootstrap["ci_high"] < 0.0,
        "quality_selective": quality_summary,
        "confidence_selective": confidence_summary,
        "relative_aurc_reduction": relative_reduction,
        "paired_aurc_difference": bootstrap,
        "fixed_80pct_coverage_diagnostic": fixed_coverage,
        "seed_start": 2000,
        "seeds_per_family": 80,
    }
    summary_path = output / "replication-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    benchmark_manifest = output / "manifest.json"
    audit_manifest = {
        "study": "H5-quality-only-replication",
        "protocol": "experiments/H5-quality-only-replication/protocol.md",
        "benchmark_manifest_sha256": hashlib.sha256(benchmark_manifest.read_bytes()).hexdigest(),
        "replication_summary_sha256": hashlib.sha256(summary_path.read_bytes()).hexdigest(),
        "decision_rule": "relative_aurc_reduction >= 0.10 and paired_ci_high < 0",
    }
    (output / "replication-manifest.json").write_text(
        json.dumps(audit_manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
