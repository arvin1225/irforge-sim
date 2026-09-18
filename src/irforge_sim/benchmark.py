"""Registered training, calibration, confirmatory evaluation and artifact export."""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

import numpy as np

from .config import CONFIRMATORY_FAMILIES, TRAIN_FAMILIES
from .detectors import (
    LearnedPixelDetector,
    DetectionResult,
    evaluate_score_map,
    image_quality_features,
    local_contrast_map,
    matched_filter_map,
    tune_threshold,
)
from .image_formation import IRSample, generate_sample
from .metrics import paired_bootstrap_conditional_error, paired_bootstrap_fixed_coverage, summarize_rows
from .selective import SelectiveRiskGate, TemperatureCalibrator, acceptance_threshold


PRIMARY_MODES = (
    "local_contrast",
    "matched_filter",
    "learned_raw",
    "learned_calibrated",
    "confidence_selective",
    "shift_selective",
)

ABLATION_MODES = (
    "quality_selective",
    "no_interactions",
    "no_calibration",
    "no_bad_pixel",
    "no_frequency",
)


@dataclass
class FittedSystem:
    detector: LearnedPixelDetector
    thresholds: dict[str, float]
    calibrator: TemperatureCalibrator
    gates: dict[str, SelectiveRiskGate]
    acceptance: dict[str, float]
    calibration_rows: list[dict[str, object]]
    train_seeds: list[tuple[str, int]]
    calibration_seeds: list[tuple[str, int]]


def _samples_for_split(train_per_family: int, calibration_per_family: int) -> tuple[list[IRSample], list[IRSample]]:
    training: list[IRSample] = []
    calibration: list[IRSample] = []
    for family_index, family in enumerate(TRAIN_FAMILIES):
        block_start = family_index * 40
        training.extend(generate_sample(block_start + offset, family) for offset in range(train_per_family))
        calibration.extend(generate_sample(block_start + 24 + offset, family) for offset in range(calibration_per_family))
    return training, calibration


def _maps(samples: list[IRSample], function: Callable[[np.ndarray], np.ndarray]) -> list[np.ndarray]:
    return [function(sample.image) for sample in samples]


def fit_system(train_per_family: int = 24, calibration_per_family: int = 16) -> FittedSystem:
    if train_per_family > 24 or calibration_per_family > 16:
        raise ValueError("registered exploratory block allows at most 24 train and 16 calibration seeds per family")
    training, calibration = _samples_for_split(train_per_family, calibration_per_family)
    detector = LearnedPixelDetector(random_state=17).fit(training)

    calibration_maps = {
        "local_contrast": _maps(calibration, local_contrast_map),
        "matched_filter": _maps(calibration, matched_filter_map),
        "learned": _maps(calibration, detector.predict_map),
    }
    thresholds = {
        "local_contrast": tune_threshold(calibration, calibration_maps["local_contrast"]),
        "matched_filter": tune_threshold(calibration, calibration_maps["matched_filter"]),
        "learned": tune_threshold(calibration, calibration_maps["learned"]),
    }
    learned_results = [
        evaluate_score_map(sample, score_map, thresholds["learned"])
        for sample, score_map in zip(calibration, calibration_maps["learned"], strict=True)
    ]
    raw_confidence = np.array([result.raw_confidence for result in learned_results])
    correctness = np.array([result.correct for result in learned_results], dtype=int)
    errors = 1 - correctness
    quality = np.stack([image_quality_features(sample.image) for sample in calibration])
    calibrator = TemperatureCalibrator.fit(raw_confidence, correctness)
    calibrated_confidence = calibrator.transform(raw_confidence)

    gate_modes = ("quality", "no_interactions", "full", "no_bad_pixel", "no_frequency")
    gates = {
        mode: SelectiveRiskGate(mode=mode, random_state=23).fit(calibrated_confidence, quality, errors)
        for mode in gate_modes
    }
    gate_raw = SelectiveRiskGate(mode="full", random_state=23).fit(raw_confidence, quality, errors)
    gates["raw_full"] = gate_raw

    learned_gate_risks = {
        "full": gates["full"].predict_risk(calibrated_confidence, quality),
        "no_interactions": gates["no_interactions"].predict_risk(calibrated_confidence, quality),
        "raw_full": gates["raw_full"].predict_risk(raw_confidence, quality),
        "no_bad_pixel": gates["no_bad_pixel"].predict_risk(calibrated_confidence, quality),
        "no_frequency": gates["no_frequency"].predict_risk(calibrated_confidence, quality),
    }
    risks = {
        "confidence": 1.0 - calibrated_confidence,
        "quality": gates["quality"].predict_risk(calibrated_confidence, quality),
        "no_interactions": 0.65 * (1.0 - calibrated_confidence) + 0.35 * learned_gate_risks["no_interactions"],
        "full": 0.65 * (1.0 - calibrated_confidence) + 0.35 * learned_gate_risks["full"],
        "raw_full": 0.65 * (1.0 - raw_confidence) + 0.35 * learned_gate_risks["raw_full"],
        "no_bad_pixel": 0.65 * (1.0 - calibrated_confidence) + 0.35 * learned_gate_risks["no_bad_pixel"],
        "no_frequency": 0.65 * (1.0 - calibrated_confidence) + 0.35 * learned_gate_risks["no_frequency"],
    }
    acceptance = {name: acceptance_threshold(values, 0.8) for name, values in risks.items()}

    calibration_rows: list[dict[str, object]] = []
    for index, (sample, result) in enumerate(zip(calibration, learned_results, strict=True)):
        calibration_rows.append(
            {
                "family": sample.config.family,
                "seed": sample.seed,
                "error": not result.correct,
                "accepted": True,
                "confidence_raw": float(raw_confidence[index]),
                "confidence_calibrated": float(calibrated_confidence[index]),
                "localized": result.localized,
                "false_alarms": result.false_alarms,
                "has_target": sample.has_target,
                "predicted_present": result.predicted_present,
            }
        )
    return FittedSystem(
        detector=detector,
        thresholds=thresholds,
        calibrator=calibrator,
        gates=gates,
        acceptance=acceptance,
        calibration_rows=calibration_rows,
        train_seeds=[(sample.config.family, sample.seed) for sample in training],
        calibration_seeds=[(sample.config.family, sample.seed) for sample in calibration],
    )


def _base_row(sample: IRSample, result: DetectionResult) -> dict[str, object]:
    row: dict[str, object] = {
        "family": sample.config.family,
        "seed": sample.seed,
        "has_target": sample.has_target,
        "localized": result.localized,
        "predicted_present": result.predicted_present,
        "false_alarms": result.false_alarms,
        "error": not result.correct,
        "top_score": result.top_score,
        "target_x": sample.target_xy[0] if sample.target_xy else -1,
        "target_y": sample.target_xy[1] if sample.target_xy else -1,
        "peak_x": result.top_xy[0],
        "peak_y": result.top_xy[1],
        "latent_contrast": sample.latent_contrast,
        "transmission": sample.config.transmission,
    }
    for name, value in sample.config.as_dict().items():
        if name != "family":
            row[name] = value
    return row


def evaluate_sample(system: FittedSystem, sample: IRSample, include_ablations: bool = True) -> list[dict[str, object]]:
    local_result = evaluate_score_map(sample, local_contrast_map(sample.image), system.thresholds["local_contrast"])
    matched_result = evaluate_score_map(sample, matched_filter_map(sample.image), system.thresholds["matched_filter"])
    learned_result = evaluate_score_map(sample, system.detector.predict_map(sample.image), system.thresholds["learned"])
    quality = image_quality_features(sample.image)[None, :]
    raw_confidence = learned_result.raw_confidence
    calibrated_confidence = float(system.calibrator.transform(raw_confidence)[0])

    gate_predictions = {
        "no_interactions": float(system.gates["no_interactions"].predict_risk(np.array([calibrated_confidence]), quality)[0]),
        "full": float(system.gates["full"].predict_risk(np.array([calibrated_confidence]), quality)[0]),
        "raw_full": float(system.gates["raw_full"].predict_risk(np.array([raw_confidence]), quality)[0]),
        "no_bad_pixel": float(system.gates["no_bad_pixel"].predict_risk(np.array([calibrated_confidence]), quality)[0]),
        "no_frequency": float(system.gates["no_frequency"].predict_risk(np.array([calibrated_confidence]), quality)[0]),
    }
    risk_values = {
        "confidence": 1.0 - calibrated_confidence,
        "quality": float(system.gates["quality"].predict_risk(np.array([calibrated_confidence]), quality)[0]),
        "no_interactions": 0.65 * (1.0 - calibrated_confidence) + 0.35 * gate_predictions["no_interactions"],
        "full": 0.65 * (1.0 - calibrated_confidence) + 0.35 * gate_predictions["full"],
        "raw_full": 0.65 * (1.0 - raw_confidence) + 0.35 * gate_predictions["raw_full"],
        "no_bad_pixel": 0.65 * (1.0 - calibrated_confidence) + 0.35 * gate_predictions["no_bad_pixel"],
        "no_frequency": 0.65 * (1.0 - calibrated_confidence) + 0.35 * gate_predictions["no_frequency"],
    }

    specifications: list[tuple[str, DetectionResult, float, float, bool]] = [
        ("local_contrast", local_result, local_result.raw_confidence, 1.0 - local_result.raw_confidence, True),
        ("matched_filter", matched_result, matched_result.raw_confidence, 1.0 - matched_result.raw_confidence, True),
        ("learned_raw", learned_result, raw_confidence, 1.0 - raw_confidence, True),
        ("learned_calibrated", learned_result, calibrated_confidence, 1.0 - calibrated_confidence, True),
        (
            "confidence_selective",
            learned_result,
            calibrated_confidence,
            risk_values["confidence"],
            risk_values["confidence"] <= system.acceptance["confidence"],
        ),
        (
            "shift_selective",
            learned_result,
            calibrated_confidence,
            risk_values["full"],
            risk_values["full"] <= system.acceptance["full"],
        ),
    ]
    if include_ablations:
        specifications.extend(
            [
                ("quality_selective", learned_result, calibrated_confidence, risk_values["quality"], risk_values["quality"] <= system.acceptance["quality"]),
                ("no_interactions", learned_result, calibrated_confidence, risk_values["no_interactions"], risk_values["no_interactions"] <= system.acceptance["no_interactions"]),
                ("no_calibration", learned_result, raw_confidence, risk_values["raw_full"], risk_values["raw_full"] <= system.acceptance["raw_full"]),
                ("no_bad_pixel", learned_result, calibrated_confidence, risk_values["no_bad_pixel"], risk_values["no_bad_pixel"] <= system.acceptance["no_bad_pixel"]),
                ("no_frequency", learned_result, calibrated_confidence, risk_values["no_frequency"], risk_values["no_frequency"] <= system.acceptance["no_frequency"]),
            ]
        )

    rows: list[dict[str, object]] = []
    for mode, result, confidence, risk_score, accepted in specifications:
        row = _base_row(sample, result)
        row.update(
            {
                "mode": mode,
                "confidence": float(confidence),
                "risk_score": float(risk_score),
                "accepted": bool(accepted),
                "silent_failure": bool((not result.correct) and accepted and confidence >= 0.8),
            }
        )
        rows.append(row)
    return rows


def _calibration_summary(system: FittedSystem) -> dict[str, object]:
    rows = system.calibration_rows
    output: dict[str, object] = {}
    for confidence_name in ("confidence_raw", "confidence_calibrated"):
        converted = []
        for row in rows:
            converted.append(
                {
                    **row,
                    "confidence": row[confidence_name],
                    "risk_score": 1.0 - float(row[confidence_name]),
                }
            )
        output[confidence_name] = summarize_rows(converted)
    family_silent_raw: dict[str, float] = {}
    family_silent_calibrated: dict[str, float] = {}
    for family in TRAIN_FAMILIES:
        subset = [row for row in rows if row["family"] == family]
        family_silent_raw[family] = float(np.mean([bool(row["error"]) and float(row["confidence_raw"]) >= 0.8 for row in subset]))
        family_silent_calibrated[family] = float(np.mean([bool(row["error"]) and float(row["confidence_calibrated"]) >= 0.8 for row in subset]))
    output["silent_failure_by_family_raw"] = family_silent_raw
    output["silent_failure_by_family_calibrated"] = family_silent_calibrated
    output["max_single_shift_silent_failure"] = max(family_silent_raw.values())
    return output


def _code_hash(project_root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted((project_root / "src" / "irforge_sim").glob("*.py")):
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def summarize_benchmark(rows: list[dict[str, object]], system: FittedSystem, bootstrap_resamples: int) -> dict[str, object]:
    primary_rows = [row for row in rows if row["mode"] in PRIMARY_MODES]
    overall = {mode: summarize_rows(row for row in primary_rows if row["mode"] == mode) for mode in PRIMARY_MODES}
    by_family = {
        family: {mode: summarize_rows(row for row in primary_rows if row["family"] == family and row["mode"] == mode) for mode in PRIMARY_MODES}
        for family in CONFIRMATORY_FAMILIES
    }
    ablations = {
        mode: summarize_rows(row for row in rows if row["mode"] == mode)
        for mode in ABLATION_MODES
        if any(row["mode"] == mode for row in rows)
    }
    confidence_rows = [row for row in rows if row["mode"] == "confidence_selective"]
    shift_rows = [row for row in rows if row["mode"] == "shift_selective"]
    bootstrap = paired_bootstrap_conditional_error(shift_rows, confidence_rows, resamples=bootstrap_resamples)
    fixed_coverage = paired_bootstrap_fixed_coverage(shift_rows, confidence_rows, coverage=0.8, resamples=bootstrap_resamples)
    calibration = _calibration_summary(system)

    confirm_family_silent = {
        family: float(by_family[family]["learned_raw"]["silent_failure_rate"])
        for family in CONFIRMATORY_FAMILIES
    }
    h1_count = sum(value > float(calibration["max_single_shift_silent_failure"]) for value in confirm_family_silent.values())
    raw_ece = float(overall["learned_raw"]["ece"])
    calibrated_ece = float(overall["learned_calibrated"]["ece"])
    raw_aurc = float(overall["learned_raw"]["aurc"])
    calibrated_aurc = float(overall["learned_calibrated"]["aurc"])
    aurc_improvement = (raw_aurc - calibrated_aurc) / max(raw_aurc, 1e-9)
    confidence_risk = float(overall["confidence_selective"]["conditional_error"])
    shift_risk = float(overall["shift_selective"]["conditional_error"])
    relative_reduction = (confidence_risk - shift_risk) / max(confidence_risk, 1e-9)
    coverage_gap = abs(float(overall["shift_selective"]["coverage"]) - float(overall["confidence_selective"]["coverage"]))
    confidence_aurc = float(overall["confidence_selective"]["aurc"])
    shift_aurc = float(overall["shift_selective"]["aurc"])
    shift_aurc_reduction = (confidence_aurc - shift_aurc) / max(confidence_aurc, 1e-9)
    hypotheses = {
        "H1_composed_silent_failure": {
            "pass": h1_count >= 2,
            "families_exceeding_single_shift_max": h1_count,
            "single_shift_max": calibration["max_single_shift_silent_failure"],
            "confirmatory_by_family": confirm_family_silent,
        },
        "H2_calibration_not_ranking": {
            "pass": calibrated_ece < raw_ece and aurc_improvement <= 0.05,
            "raw_ece": raw_ece,
            "calibrated_ece": calibrated_ece,
            "relative_aurc_improvement": aurc_improvement,
        },
        "H3_shift_selective": {
            "pass": relative_reduction >= 0.20 and coverage_gap <= 0.10 and bootstrap["ci_high"] < 0.0,
            "confidence_conditional_error": confidence_risk,
            "shift_conditional_error": shift_risk,
            "relative_reduction": relative_reduction,
            "coverage_gap": coverage_gap,
            "paired_difference": bootstrap,
        },
        "H4_fixed_coverage_ranking": {
            "pass": shift_aurc_reduction >= 0.05 and fixed_coverage["difference"] < 0.0 and fixed_coverage["ci_high"] < 0.0,
            "confidence_aurc": confidence_aurc,
            "shift_aurc": shift_aurc,
            "relative_aurc_reduction": shift_aurc_reduction,
            "fixed_coverage_comparison": fixed_coverage,
        },
    }
    return {
        "registered_success": all(hypotheses[name]["pass"] for name in ("H1_composed_silent_failure", "H2_calibration_not_ranking", "H3_shift_selective")),
        "failure_ranking_contribution_supported": bool(hypotheses["H2_calibration_not_ranking"]["pass"] and hypotheses["H4_fixed_coverage_ranking"]["pass"]),
        "overall": overall,
        "by_family": by_family,
        "ablations": ablations,
        "calibration": calibration,
        "hypotheses": hypotheses,
    }


def run_benchmark(
    out_dir: str | Path,
    *,
    confirm_seed_start: int = 1000,
    seeds_per_family: int = 80,
    train_per_family: int = 24,
    calibration_per_family: int = 16,
    bootstrap_resamples: int = 5000,
    include_ablations: bool = True,
) -> dict[str, object]:
    if confirm_seed_start not in {1000, 2000} and seeds_per_family >= 80:
        raise ValueError("full runs must use a frozen seed start: 1000 confirmation or 2000 replication")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    system = fit_system(train_per_family=train_per_family, calibration_per_family=calibration_per_family)
    rows: list[dict[str, object]] = []
    for family in CONFIRMATORY_FAMILIES:
        for offset in range(seeds_per_family):
            sample = generate_sample(confirm_seed_start + offset, family)
            rows.extend(evaluate_sample(system, sample, include_ablations=include_ablations))

    fieldnames = list(rows[0].keys())
    csv_path = out / "benchmark.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    summary = summarize_benchmark(rows, system, bootstrap_resamples=bootstrap_resamples)
    summary_path = out / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    project_root = Path(__file__).resolve().parents[2]
    manifest = {
        "artifact": "IRForge-Sim confirmatory benchmark" if confirm_seed_start == 1000 else "IRForge-Sim H5 replication benchmark",
        "protocol": (
            "experiments/H1-composed-shift-boundary/protocol.md"
            if confirm_seed_start == 1000
            else "experiments/H5-quality-only-replication/protocol.md"
        ),
        "confirmatory_seed_start": confirm_seed_start,
        "seeds_per_family": seeds_per_family,
        "families": list(CONFIRMATORY_FAMILIES),
        "modes": list(PRIMARY_MODES + (ABLATION_MODES if include_ablations else ())),
        "row_count": len(rows),
        "train_seeds": system.train_seeds,
        "calibration_seeds": system.calibration_seeds,
        "thresholds": system.thresholds,
        "temperature": system.calibrator.temperature,
        "acceptance_thresholds": system.acceptance,
        "bootstrap_resamples": bootstrap_resamples,
        "code_sha256": _code_hash(project_root),
        "benchmark_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
        "summary_sha256": hashlib.sha256(summary_path.read_bytes()).hexdigest(),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return {"rows": rows, "summary": summary, "manifest": manifest, "system": system}
