"""Target-level, calibration and selective-prediction metrics."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np


def expected_calibration_error(confidence: np.ndarray, correctness: np.ndarray, bins: int = 10) -> float:
    confidence = np.asarray(confidence, dtype=float)
    correctness = np.asarray(correctness, dtype=float)
    edges = np.linspace(0.0, 1.0, bins + 1)
    value = 0.0
    for index in range(bins):
        if index == bins - 1:
            mask = (confidence >= edges[index]) & (confidence <= edges[index + 1])
        else:
            mask = (confidence >= edges[index]) & (confidence < edges[index + 1])
        if np.any(mask):
            value += np.mean(mask) * abs(float(np.mean(confidence[mask]) - np.mean(correctness[mask])))
    return float(value)


def risk_coverage_curve(errors: np.ndarray, risks: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    errors = np.asarray(errors, dtype=float)
    order = np.argsort(np.asarray(risks, dtype=float), kind="stable")
    ranked_errors = errors[order]
    coverage = np.arange(1, len(errors) + 1, dtype=float) / max(1, len(errors))
    risk = np.cumsum(ranked_errors) / np.arange(1, len(errors) + 1)
    return coverage, risk


def aurc(errors: np.ndarray, risks: np.ndarray) -> float:
    coverage, risk = risk_coverage_curve(errors, risks)
    if len(coverage) < 2:
        return float(risk[0]) if len(risk) else 0.0
    return float(np.trapezoid(risk, coverage))


def summarize_rows(rows: Iterable[dict[str, object]]) -> dict[str, float | int]:
    records = list(rows)
    if not records:
        return {}
    accepted = np.array([bool(row["accepted"]) for row in records])
    errors = np.array([bool(row["error"]) for row in records], dtype=bool)
    confidence = np.array([float(row["confidence"]) for row in records])
    risk_score = np.array([float(row["risk_score"]) for row in records])
    has_target = np.array([bool(row["has_target"]) for row in records])
    localized = np.array([bool(row["localized"]) for row in records])
    false_alarms = np.array([int(row["false_alarms"]) for row in records])
    predicted_present = np.array([bool(row["predicted_present"]) for row in records])
    tp = int(np.sum(has_target & localized))
    fn = int(np.sum(has_target & ~localized))
    fp_images = int(np.sum(~has_target & predicted_present))
    f1 = 2.0 * tp / max(1.0, 2.0 * tp + fp_images + fn)
    return {
        "n": len(records),
        "pd": float(tp / max(1, np.sum(has_target))),
        "false_alarms_per_image": float(np.mean(false_alarms)),
        "target_f1": float(f1),
        "ece": expected_calibration_error(confidence, 1.0 - errors.astype(float)),
        "aurc": aurc(errors.astype(float), risk_score),
        "coverage": float(np.mean(accepted)),
        "conditional_error": float(np.mean(errors[accepted])) if np.any(accepted) else 1.0,
        "silent_failure_rate": float(np.mean(errors & accepted & (confidence >= 0.8))),
        "accepted_errors": int(np.sum(errors[accepted])) if np.any(accepted) else 0,
    }


def paired_bootstrap_conditional_error(
    rows_a: list[dict[str, object]],
    rows_b: list[dict[str, object]],
    *,
    resamples: int = 5000,
    seed: int = 20260803,
) -> dict[str, float]:
    if len(rows_a) != len(rows_b):
        raise ValueError("paired rows must have equal length")
    keys_a = [(row["family"], int(row["seed"])) for row in rows_a]
    keys_b = [(row["family"], int(row["seed"])) for row in rows_b]
    if keys_a != keys_b:
        raise ValueError("paired rows are not aligned")
    error_a = np.array([bool(row["error"]) for row in rows_a], dtype=float)
    error_b = np.array([bool(row["error"]) for row in rows_b], dtype=float)
    accept_a = np.array([bool(row["accepted"]) for row in rows_a])
    accept_b = np.array([bool(row["accepted"]) for row in rows_b])

    def statistic(indices: np.ndarray) -> float:
        a_mask, b_mask = accept_a[indices], accept_b[indices]
        risk_a = float(np.mean(error_a[indices][a_mask])) if np.any(a_mask) else 1.0
        risk_b = float(np.mean(error_b[indices][b_mask])) if np.any(b_mask) else 1.0
        return risk_a - risk_b

    rng = np.random.default_rng(seed)
    samples = np.empty(resamples, dtype=float)
    for index in range(resamples):
        indices = rng.integers(0, len(rows_a), size=len(rows_a))
        samples[index] = statistic(indices)
    return {
        "difference": statistic(np.arange(len(rows_a))),
        "ci_low": float(np.quantile(samples, 0.025)),
        "ci_high": float(np.quantile(samples, 0.975)),
    }


def paired_bootstrap_fixed_coverage(
    rows_a: list[dict[str, object]],
    rows_b: list[dict[str, object]],
    *,
    coverage: float = 0.8,
    resamples: int = 5000,
    seed: int = 20260804,
) -> dict[str, float]:
    """Compare two risk rankings at the same exact, label-free coverage."""

    if len(rows_a) != len(rows_b):
        raise ValueError("paired rows must have equal length")
    keys_a = [(row["family"], int(row["seed"])) for row in rows_a]
    keys_b = [(row["family"], int(row["seed"])) for row in rows_b]
    if keys_a != keys_b:
        raise ValueError("paired rows are not aligned")
    error_a = np.array([bool(row["error"]) for row in rows_a], dtype=float)
    error_b = np.array([bool(row["error"]) for row in rows_b], dtype=float)
    risk_a = np.array([float(row["risk_score"]) for row in rows_a])
    risk_b = np.array([float(row["risk_score"]) for row in rows_b])

    def statistic(indices: np.ndarray) -> tuple[float, float, float]:
        keep = max(1, int(round(coverage * len(indices))))
        order_a = np.argsort(risk_a[indices], kind="stable")[:keep]
        order_b = np.argsort(risk_b[indices], kind="stable")[:keep]
        value_a = float(np.mean(error_a[indices][order_a]))
        value_b = float(np.mean(error_b[indices][order_b]))
        return value_a - value_b, value_a, value_b

    rng = np.random.default_rng(seed)
    differences = np.empty(resamples, dtype=float)
    for index in range(resamples):
        sample_indices = rng.integers(0, len(rows_a), size=len(rows_a))
        differences[index] = statistic(sample_indices)[0]
    difference, risk_a_value, risk_b_value = statistic(np.arange(len(rows_a)))
    return {
        "coverage": coverage,
        "difference": difference,
        "risk_a": risk_a_value,
        "risk_b": risk_b_value,
        "ci_low": float(np.quantile(differences, 0.025)),
        "ci_high": float(np.quantile(differences, 0.975)),
    }


def paired_bootstrap_aurc(
    rows_a: list[dict[str, object]],
    rows_b: list[dict[str, object]],
    *,
    resamples: int = 5000,
    seed: int = 20260805,
) -> dict[str, float]:
    """Paired seed bootstrap for the difference between two empirical AURCs."""

    if len(rows_a) != len(rows_b):
        raise ValueError("paired rows must have equal length")
    keys_a = [(row["family"], int(row["seed"])) for row in rows_a]
    keys_b = [(row["family"], int(row["seed"])) for row in rows_b]
    if keys_a != keys_b:
        raise ValueError("paired rows are not aligned")
    errors = np.array([bool(row["error"]) for row in rows_a], dtype=float)
    if not np.array_equal(errors, np.array([bool(row["error"]) for row in rows_b], dtype=float)):
        raise ValueError("risk rankings must describe the same detector errors")
    risk_a = np.array([float(row["risk_score"]) for row in rows_a])
    risk_b = np.array([float(row["risk_score"]) for row in rows_b])

    def statistic(indices: np.ndarray) -> float:
        return aurc(errors[indices], risk_a[indices]) - aurc(errors[indices], risk_b[indices])

    rng = np.random.default_rng(seed)
    values = np.empty(resamples, dtype=float)
    for index in range(resamples):
        indices = rng.integers(0, len(rows_a), size=len(rows_a))
        values[index] = statistic(indices)
    return {
        "difference": statistic(np.arange(len(rows_a))),
        "ci_low": float(np.quantile(values, 0.025)),
        "ci_high": float(np.quantile(values, 0.975)),
    }
