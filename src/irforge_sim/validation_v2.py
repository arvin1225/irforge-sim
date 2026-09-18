"""Independent H6 artifact integrity and research-contract validation."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

from .benchmark import _code_hash
from .benchmark_v2 import (
    DETECTOR_METHODS,
    FRAMES_PER_SEQUENCE,
    SELECTIVE_METHODS,
    sequence_sha256,
    summarize_h6,
)
from .temporal import CALIBRATION_DRIFTS, HELDOUT_DRIFTS, generate_sequence


BOOL_FIELDS = {"has_target", "accepted", "error", "localized"}
INT_FIELDS = {"sequence_seed", "frame_index", "false_alarms"}


def _parse(row: dict[str, str]) -> dict[str, object]:
    parsed: dict[str, object] = {}
    for key, value in row.items():
        if key in BOOL_FIELDS:
            parsed[key] = value == "True"
        elif key in INT_FIELDS:
            parsed[key] = int(value)
        elif key in {"regime", "family", "method"}:
            parsed[key] = value
        else:
            parsed[key] = float(value)
    return parsed


def validate_h6_artifact(path: str | Path) -> dict[str, object]:
    artifact = Path(path)
    csv_path = artifact / "benchmark_h6.csv"
    summary_path = artifact / "summary_h6.json"
    manifest = json.loads((artifact / "manifest_h6.json").read_text(encoding="utf-8"))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = [_parse(row) for row in csv.DictReader(handle)]
    methods = DETECTOR_METHODS + SELECTIVE_METHODS
    expected = {
        ("matched", family, seed, frame, method)
        for family in CALIBRATION_DRIFTS
        for seed in range(3500, 3540)
        for frame in range(FRAMES_PER_SEQUENCE)
        for method in methods
    } | {
        ("heldout", family, seed, frame, method)
        for family in HELDOUT_DRIFTS
        for seed in range(4000, 4080)
        for frame in range(FRAMES_PER_SEQUENCE)
        for method in methods
    }
    counts = Counter(
        (str(row["regime"]), str(row["family"]), int(row["sequence_seed"]), int(row["frame_index"]), str(row["method"]))
        for row in rows
    )
    calibration_ids = {(family, seed) for family in CALIBRATION_DRIFTS for seed in range(3000, 3040)}
    evaluation_ids = {(str(row["family"]), int(row["sequence_seed"])) for row in rows}
    recomputed = summarize_h6(rows, int(manifest["bootstrap_resamples"]))
    repo_root = Path(__file__).resolve().parents[2]
    checks: dict[str, bool] = {
        "benchmark_hash": hashlib.sha256(csv_path.read_bytes()).hexdigest() == manifest["benchmark_sha256"],
        "summary_hash": hashlib.sha256(summary_path.read_bytes()).hexdigest() == manifest["summary_sha256"],
        "code_hash": _code_hash(repo_root) == manifest["code_sha256"],
        "row_count": len(rows) == 34_560 == int(manifest["row_count"]),
        "complete_matrix": set(counts) == expected and all(value == 1 for value in counts.values()),
        "split_disjointness": calibration_ids.isdisjoint(evaluation_ids),
        "finite_metrics": all(
            math.isfinite(float(row[key]))
            for row in rows
            for key in ("drift_magnitude", "drift_score", "confidence", "risk_score")
        ),
        "crc_calibration_contract": all(
            float(values["corrected_risk"]) <= float(manifest["alpha"]) + 1e-12
            and int(values["sequence_count"]) == 120
            for values in manifest["crc_calibration"].values()
        ),
        "hypothesis_reproduction": recomputed["hypotheses"] == summary["hypotheses"],
        "summary_success_reproduction": bool(recomputed["registered_success"]) == bool(summary["registered_success"]),
        "matched_replay": sequence_sha256(generate_sequence(3500, "gain_ramp", frames=FRAMES_PER_SEQUENCE))
        == manifest["deterministic_sequence_replays"]["matched/gain_ramp/3500"],
        "heldout_replay": sequence_sha256(generate_sequence(4007, "compound_aging", frames=FRAMES_PER_SEQUENCE))
        == manifest["deterministic_sequence_replays"]["heldout/compound_aging/4007"],
    }
    report = {
        "integrity": all(checks.values()),
        "registered_success": bool(summary["registered_success"]),
        "checks": checks,
        "manifest": manifest,
        "interpretation": "Matched-drift CRC validity and held-out robustness are separate; artifact integrity does not imply H6 success.",
    }
    (artifact / "validation-report-h6.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def reseal_h6_code_hash(path: str | Path) -> dict[str, object]:
    """Refresh only the code fingerprint after an outcome-neutral refactor."""

    artifact = Path(path)
    manifest_path = artifact / "manifest_h6.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["code_sha256"] = _code_hash(Path(__file__).resolve().parents[2])
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest
