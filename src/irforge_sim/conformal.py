"""Sequence-level conformal risk control for bounded false-release loss."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class CRCCalibration:
    alpha: float
    threshold: float
    sequence_count: int
    calibration_loss_count: int
    corrected_risk: float
    calibration_frame_coverage: float


def sequence_crc_threshold(
    sequence_risks: list[np.ndarray],
    sequence_errors: list[np.ndarray],
    *,
    alpha: float = 0.10,
) -> CRCCalibration:
    if len(sequence_risks) != len(sequence_errors) or not sequence_risks:
        raise ValueError("aligned non-empty sequence risks and errors are required")
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be in (0, 1)")
    for risks, errors in zip(sequence_risks, sequence_errors, strict=True):
        if len(risks) != len(errors) or len(risks) == 0:
            raise ValueError("every sequence must contain aligned frames")
    candidates = np.unique(np.concatenate([np.asarray(values, dtype=float) for values in sequence_risks]))
    candidates = np.concatenate((np.array([-np.inf]), candidates))
    n = len(sequence_risks)
    selected = float("-inf")
    selected_losses = 0
    selected_coverage = 0.0
    for threshold in candidates:
        losses = []
        accepted = 0
        frames = 0
        for risks, errors in zip(sequence_risks, sequence_errors, strict=True):
            mask = np.asarray(risks, dtype=float) <= threshold
            losses.append(bool(np.any(mask & np.asarray(errors, dtype=bool))))
            accepted += int(np.sum(mask))
            frames += len(mask)
        loss_count = int(np.sum(losses))
        corrected = (loss_count + 1.0) / (n + 1.0)
        if corrected <= alpha + 1e-12:
            selected = float(threshold)
            selected_losses = loss_count
            selected_coverage = accepted / max(frames, 1)
    return CRCCalibration(
        alpha=float(alpha),
        threshold=selected,
        sequence_count=n,
        calibration_loss_count=selected_losses,
        corrected_risk=float((selected_losses + 1.0) / (n + 1.0)),
        calibration_frame_coverage=float(selected_coverage),
    )


def wilson_upper(errors: int, total: int, confidence: float = 0.95) -> float:
    if total <= 0:
        return 1.0
    z = 1.6448536269514722 if confidence == 0.95 else 1.959963984540054
    p = errors / total
    denominator = 1.0 + z * z / total
    center = p + z * z / (2.0 * total)
    radius = z * np.sqrt(p * (1.0 - p) / total + z * z / (4.0 * total * total))
    return float((center + radius) / denominator)

