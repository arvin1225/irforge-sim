"""Frozen H6 temporal-drift and sequence conformal-risk benchmark."""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from .benchmark import _code_hash, fit_system
from .conformal import CRCCalibration, sequence_crc_threshold, wilson_upper
from .detectors import evaluate_score_map, image_quality_features, local_contrast_map, matched_filter_map, tune_threshold
from .metrics import aurc
from .temporal import CALIBRATION_DRIFTS, HELDOUT_DRIFTS, IRSequence, generate_sequence, temporal_residual_maps


FRAMES_PER_SEQUENCE = 12
SELECTIVE_METHODS = ("fixed80_confidence", "crc_confidence", "crc_quality", "crc_temporal")
DETECTOR_METHODS = ("local_contrast_frame", "matched_filter_frame", "learned_frame", "temporal_residual")


@dataclass
class SequenceObservation:
    sequence: IRSequence
    frame_records: list[dict[str, object]]


def _generate_block(families: tuple[str, ...], seed_start: int, count: int) -> list[IRSequence]:
    return [generate_sequence(seed, family, frames=FRAMES_PER_SEQUENCE) for family in families for seed in range(seed_start, seed_start + count)]


def sequence_sha256(sequence: IRSequence) -> str:
    digest = hashlib.sha256()
    digest.update(sequence.drift_family.encode())
    digest.update(str(sequence.sequence_seed).encode())
    for frame, magnitude in zip(sequence.frames, sequence.drift_magnitudes, strict=True):
        digest.update(frame.image.tobytes())
        digest.update(frame.target_mask.tobytes())
        digest.update(np.float64(magnitude).tobytes())
    return digest.hexdigest()


def _fit_temporal_threshold(sequences: list[IRSequence]) -> float:
    samples = [frame for sequence in sequences for frame in sequence.frames]
    maps = [score for sequence in sequences for score in temporal_residual_maps(sequence)]
    return tune_threshold(samples, maps)


def _observe_sequence(system: object, sequence: IRSequence, temporal_threshold: float) -> SequenceObservation:
    temporal_maps = temporal_residual_maps(sequence)
    records: list[dict[str, object]] = []
    first_quality: np.ndarray | None = None
    previous_confidence: float | None = None
    for frame_index, (frame, temporal_map) in enumerate(zip(sequence.frames, temporal_maps, strict=True)):
        local = evaluate_score_map(frame, local_contrast_map(frame.image), system.thresholds["local_contrast"])
        matched = evaluate_score_map(frame, matched_filter_map(frame.image), system.thresholds["matched_filter"])
        learned = evaluate_score_map(frame, system.detector.predict_map(frame.image), system.thresholds["learned"])
        temporal = evaluate_score_map(frame, temporal_map, temporal_threshold)
        quality = image_quality_features(frame.image)
        if first_quality is None:
            first_quality = quality.copy()
        calibrated_confidence = float(system.calibrator.transform(learned.raw_confidence)[0])
        confidence_risk = 1.0 - calibrated_confidence
        quality_risk = float(system.gates["quality"].predict_risk(np.array([calibrated_confidence]), quality[None, :])[0])
        quality_change = float(np.mean(np.abs(quality - first_quality) / (np.abs(first_quality) + 0.02)))
        confidence_change = abs(calibrated_confidence - previous_confidence) if previous_confidence is not None else 0.0
        drift_raw = quality_change + 0.35 * confidence_change
        previous_confidence = calibrated_confidence
        records.append(
            {
                "frame_index": frame_index,
                "has_target": frame.has_target,
                "learned_error": not learned.correct,
                "confidence": calibrated_confidence,
                "confidence_risk": confidence_risk,
                "quality_risk": quality_risk,
                "drift_raw": drift_raw,
                "quality": quality,
                "local": local,
                "matched": matched,
                "learned": learned,
                "temporal": temporal,
            }
        )
    return SequenceObservation(sequence, records)


def _score_observations(observations: list[SequenceObservation], drift_scale: float) -> None:
    for observation in observations:
        for record in observation.frame_records:
            drift_score = float(np.clip(float(record["drift_raw"]) / max(drift_scale, 1e-9), 0.0, 1.0))
            record["drift_score"] = drift_score
            record["temporal_risk"] = (
                0.50 * float(record["quality_risk"])
                + 0.25 * float(record["confidence_risk"])
                + 0.25 * drift_score
            )


def _risk_sequences(observations: list[SequenceObservation], key: str) -> list[np.ndarray]:
    return [np.array([float(record[key]) for record in observation.frame_records]) for observation in observations]


def _error_sequences(observations: list[SequenceObservation]) -> list[np.ndarray]:
    return [np.array([bool(record["learned_error"]) for record in observation.frame_records]) for observation in observations]


def _calibrate_controllers(observations: list[SequenceObservation]) -> tuple[dict[str, float], dict[str, CRCCalibration]]:
    errors = _error_sequences(observations)
    risk_keys = {"crc_confidence": "confidence_risk", "crc_quality": "quality_risk", "crc_temporal": "temporal_risk"}
    controllers = {
        method: sequence_crc_threshold(_risk_sequences(observations, key), errors, alpha=0.10)
        for method, key in risk_keys.items()
    }
    confidence = np.concatenate(_risk_sequences(observations, "confidence_risk"))
    thresholds = {"fixed80_confidence": float(np.quantile(confidence, 0.80, method="higher"))}
    thresholds.update({method: controller.threshold for method, controller in controllers.items()})
    return thresholds, controllers


def _base_frame_row(observation: SequenceObservation, record: dict[str, object], regime: str) -> dict[str, object]:
    sequence = observation.sequence
    return {
        "regime": regime,
        "family": sequence.drift_family,
        "sequence_seed": sequence.sequence_seed,
        "frame_index": int(record["frame_index"]),
        "has_target": bool(record["has_target"]),
        "drift_magnitude": float(sequence.drift_magnitudes[int(record["frame_index"])]),
        "drift_score": float(record["drift_score"]),
    }


def _frame_rows(
    observations: list[SequenceObservation],
    thresholds: dict[str, float],
    regime: str,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    risk_keys = {
        "fixed80_confidence": "confidence_risk",
        "crc_confidence": "confidence_risk",
        "crc_quality": "quality_risk",
        "crc_temporal": "temporal_risk",
    }
    for observation in observations:
        for record in observation.frame_records:
            for method, result_key in (
                ("local_contrast_frame", "local"),
                ("matched_filter_frame", "matched"),
                ("learned_frame", "learned"),
                ("temporal_residual", "temporal"),
            ):
                result = record[result_key]
                row = _base_frame_row(observation, record, regime)
                row.update(
                    {
                        "method": method,
                        "accepted": True,
                        "error": not result.correct,
                        "localized": result.localized,
                        "false_alarms": result.false_alarms,
                        "confidence": result.raw_confidence,
                        "risk_score": 1.0 - result.raw_confidence,
                    }
                )
                rows.append(row)
            learned = record["learned"]
            for method, risk_key in risk_keys.items():
                risk = float(record[risk_key])
                row = _base_frame_row(observation, record, regime)
                row.update(
                    {
                        "method": method,
                        "accepted": risk <= thresholds[method],
                        "error": bool(record["learned_error"]),
                        "localized": learned.localized,
                        "false_alarms": learned.false_alarms,
                        "confidence": float(record["confidence"]),
                        "risk_score": risk,
                    }
                )
                rows.append(row)
    return rows


def _selector_summary(rows: list[dict[str, object]]) -> dict[str, float | int]:
    if not rows:
        return {}
    keys = sorted({(str(row["family"]), int(row["sequence_seed"])) for row in rows})
    sequence_losses = []
    for family, seed in keys:
        subset = [row for row in rows if row["family"] == family and int(row["sequence_seed"]) == seed]
        sequence_losses.append(any(bool(row["accepted"]) and bool(row["error"]) for row in subset))
    accepted = np.array([bool(row["accepted"]) for row in rows])
    errors = np.array([bool(row["error"]) for row in rows])
    sequence_errors = int(np.sum(sequence_losses))
    return {
        "sequences": len(keys),
        "sequence_false_release_probability": float(np.mean(sequence_losses)),
        "sequence_false_release_wilson_upper": wilson_upper(sequence_errors, len(keys)),
        "sequence_false_releases": sequence_errors,
        "frame_coverage": float(np.mean(accepted)),
        "frame_conditional_error": float(np.mean(errors[accepted])) if np.any(accepted) else 1.0,
        "frame_aurc": aurc(errors.astype(float), np.array([float(row["risk_score"]) for row in rows])),
        "accepted_frames": int(np.sum(accepted)),
    }


def _detector_summary(rows: list[dict[str, object]]) -> dict[str, float | int]:
    target = np.array([bool(row["has_target"]) for row in rows])
    localized = np.array([bool(row["localized"]) for row in rows])
    return {
        "frames": len(rows),
        "target_present_pd": float(np.mean(localized[target])) if np.any(target) else 0.0,
        "false_alarms_per_image": float(np.mean([int(row["false_alarms"]) for row in rows])),
        "frame_error": float(np.mean([bool(row["error"]) for row in rows])),
    }


def _matched_coverage_bootstrap(rows: list[dict[str, object]], resamples: int = 5000) -> dict[str, float]:
    temporal = [row for row in rows if row["method"] == "crc_temporal"]
    confidence = [row for row in rows if row["method"] == "fixed80_confidence"]
    keys = sorted({(str(row["family"]), int(row["sequence_seed"])) for row in temporal})
    by_method = {
        "temporal": {(str(row["family"]), int(row["sequence_seed"]), int(row["frame_index"])): row for row in temporal},
        "confidence": {(str(row["family"]), int(row["sequence_seed"]), int(row["frame_index"])): row for row in confidence},
    }
    coverage = float(np.mean([bool(row["accepted"]) for row in temporal]))
    temporal_risk = np.array(
        [[float(by_method["temporal"][(family, seed, frame)]["risk_score"]) for frame in range(FRAMES_PER_SEQUENCE)] for family, seed in keys]
    )
    confidence_risk = np.array(
        [[float(by_method["confidence"][(family, seed, frame)]["risk_score"]) for frame in range(FRAMES_PER_SEQUENCE)] for family, seed in keys]
    )
    errors = np.array(
        [[bool(by_method["temporal"][(family, seed, frame)]["error"]) for frame in range(FRAMES_PER_SEQUENCE)] for family, seed in keys],
        dtype=float,
    )

    def statistic(selected: np.ndarray) -> float:
        temp_values = temporal_risk[selected].reshape(-1)
        conf_values = confidence_risk[selected].reshape(-1)
        selected_errors = errors[selected].reshape(-1)
        keep = max(1, int(round(coverage * len(temp_values))))
        temp_order = np.argsort(temp_values, kind="stable")[:keep]
        conf_order = np.argsort(conf_values, kind="stable")[:keep]
        temp_error = float(np.mean(selected_errors[temp_order]))
        conf_error = float(np.mean(selected_errors[conf_order]))
        return temp_error - conf_error

    original = np.arange(len(keys))
    rng = np.random.default_rng(20260813)
    values = np.array([statistic(rng.integers(0, len(keys), size=len(keys))) for _ in range(resamples)])
    return {
        "coverage": coverage,
        "difference": statistic(original),
        "ci_low": float(np.quantile(values, 0.025)),
        "ci_high": float(np.quantile(values, 0.975)),
    }


def summarize_h6(rows: list[dict[str, object]], bootstrap_resamples: int) -> dict[str, object]:
    selectors = {
        regime: {
            method: _selector_summary([row for row in rows if row["regime"] == regime and row["method"] == method])
            for method in SELECTIVE_METHODS
        }
        for regime in ("matched", "heldout")
    }
    detectors = {
        family: {
            method: _detector_summary([row for row in rows if row["regime"] == "heldout" and row["family"] == family and row["method"] == method])
            for method in DETECTOR_METHODS
        }
        for family in HELDOUT_DRIFTS
    }
    matched = selectors["matched"]["crc_temporal"]
    held_temporal = selectors["heldout"]["crc_temporal"]
    held_confidence = selectors["heldout"]["crc_confidence"]
    relative_reduction = (
        float(held_confidence["sequence_false_release_probability"])
        - float(held_temporal["sequence_false_release_probability"])
    ) / max(float(held_confidence["sequence_false_release_probability"]), 1e-12)
    coverage_gap = abs(float(held_temporal["frame_coverage"]) - float(held_confidence["frame_coverage"]))
    coverage_comparison = _matched_coverage_bootstrap(
        [row for row in rows if row["regime"] == "heldout"], resamples=bootstrap_resamples
    )
    temporal_wins = 0
    fa_budget_pass = True
    for family in HELDOUT_DRIFTS:
        values = detectors[family]
        stronger = max(("local_contrast_frame", "matched_filter_frame"), key=lambda method: float(values[method]["target_present_pd"]))
        temporal_wins += int(float(values["temporal_residual"]["target_present_pd"]) > float(values[stronger]["target_present_pd"]))
        fa_budget_pass &= float(values["temporal_residual"]["false_alarms_per_image"]) <= 2.0 * max(
            float(values[stronger]["false_alarms_per_image"]), 1e-12
        )
    hypotheses = {
        "H6_A_pass": float(matched["sequence_false_release_probability"]) <= 0.10
        and float(matched["sequence_false_release_wilson_upper"]) <= 0.15
        and float(matched["frame_coverage"]) >= 0.15,
        "H6_B_pass": relative_reduction >= 0.20 and coverage_gap <= 0.10,
        "H6_C_pass": float(coverage_comparison["difference"]) < 0.0 and float(coverage_comparison["ci_high"]) < 0.0,
        "H6_D_pass": temporal_wins >= 2 and fa_budget_pass,
    }
    return {
        "selectors": selectors,
        "detectors_by_heldout_family": detectors,
        "heldout_temporal_relative_sequence_risk_reduction": relative_reduction,
        "heldout_temporal_confidence_coverage_gap": coverage_gap,
        "heldout_matched_coverage_frame_error": coverage_comparison,
        "temporal_baseline_family_wins": temporal_wins,
        "temporal_baseline_false_alarm_budget_pass": bool(fa_budget_pass),
        "hypotheses": hypotheses,
        "registered_success": all(hypotheses.values()),
    }


def run_h6_benchmark(output_dir: str | Path, *, bootstrap_resamples: int = 5000) -> dict[str, object]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    system = fit_system()
    calibration_sequences = _generate_block(CALIBRATION_DRIFTS, 3000, 40)
    temporal_threshold = _fit_temporal_threshold(calibration_sequences)
    calibration_observations = [_observe_sequence(system, sequence, temporal_threshold) for sequence in calibration_sequences]
    drift_scale = float(
        np.quantile(
            [float(record["drift_raw"]) for observation in calibration_observations for record in observation.frame_records],
            0.90,
            method="higher",
        )
    )
    _score_observations(calibration_observations, drift_scale)
    thresholds, controllers = _calibrate_controllers(calibration_observations)
    matched = [_observe_sequence(system, sequence, temporal_threshold) for sequence in _generate_block(CALIBRATION_DRIFTS, 3500, 40)]
    heldout = [_observe_sequence(system, sequence, temporal_threshold) for sequence in _generate_block(HELDOUT_DRIFTS, 4000, 80)]
    _score_observations(matched, drift_scale)
    _score_observations(heldout, drift_scale)
    rows = _frame_rows(matched, thresholds, "matched") + _frame_rows(heldout, thresholds, "heldout")
    csv_path = output / "benchmark_h6.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = summarize_h6(rows, bootstrap_resamples)
    summary_path = output / "summary_h6.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    project_root = Path(__file__).resolve().parents[2]
    manifest = {
        "artifact": "IRForge-Sim H6 temporal conformal-risk confirmation",
        "protocol": "experiments/H6-temporal-conformal-risk/protocol.md",
        "calibration": {"families": list(CALIBRATION_DRIFTS), "seed_start": 3000, "sequences_per_family": 40},
        "matched": {"families": list(CALIBRATION_DRIFTS), "seed_start": 3500, "sequences_per_family": 40},
        "heldout": {"families": list(HELDOUT_DRIFTS), "seed_start": 4000, "sequences_per_family": 80},
        "frames_per_sequence": FRAMES_PER_SEQUENCE,
        "methods": list(DETECTOR_METHODS + SELECTIVE_METHODS),
        "row_count": len(rows),
        "alpha": 0.10,
        "temporal_weights": {"quality": 0.50, "confidence": 0.25, "temporal": 0.25},
        "temporal_detector_threshold": temporal_threshold,
        "drift_scale": drift_scale,
        "acceptance_thresholds": thresholds,
        "crc_calibration": {name: asdict(value) for name, value in controllers.items()},
        "deterministic_sequence_replays": {
            "matched/gain_ramp/3500": sequence_sha256(generate_sequence(3500, "gain_ramp", frames=FRAMES_PER_SEQUENCE)),
            "heldout/compound_aging/4007": sequence_sha256(generate_sequence(4007, "compound_aging", frames=FRAMES_PER_SEQUENCE)),
        },
        "code_sha256": _code_hash(project_root),
        "benchmark_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
        "summary_sha256": hashlib.sha256(summary_path.read_bytes()).hexdigest(),
        "bootstrap_resamples": bootstrap_resamples,
    }
    (output / "manifest_h6.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return {"rows": rows, "summary": summary, "manifest": manifest}
