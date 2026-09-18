"""Replayable infrared sequences with target motion and sensor-state drift."""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np
from scipy.ndimage import gaussian_filter

from .detectors import _robust_probability
from .image_formation import IRSample, generate_sample


CALIBRATION_DRIFTS = ("gain_ramp", "fpn_ramp", "blur_creep")
HELDOUT_DRIFTS = ("bad_pixel_bloom", "oscillatory_gain", "compound_aging")
ALL_DRIFTS = CALIBRATION_DRIFTS + HELDOUT_DRIFTS


@dataclass(frozen=True)
class IRSequence:
    sequence_seed: int
    drift_family: str
    frames: tuple[IRSample, ...]
    drift_magnitudes: tuple[float, ...]


def _spot(size: int, x: float, y: float, sigma: float) -> np.ndarray:
    yy, xx = np.mgrid[0:size, 0:size]
    return np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2.0 * sigma**2))


def _sensor_drift(
    image: np.ndarray,
    family: str,
    tau: float,
    frame_index: int,
    rng: np.random.Generator,
    row_pattern: np.ndarray,
    col_pattern: np.ndarray,
    bad_order: np.ndarray,
) -> tuple[np.ndarray, float]:
    output = np.asarray(image, dtype=float).copy()
    magnitude = 0.0
    if family == "gain_ramp":
        gain, offset = 1.0 + 0.18 * tau, 0.035 * tau
        output = gain * output + offset
        magnitude = abs(gain - 1.0) + abs(offset)
    elif family == "fpn_ramp":
        amplitude = 0.055 * tau
        output = output * (1.0 + amplitude * row_pattern) + 0.032 * tau * col_pattern
        magnitude = amplitude + 0.032 * tau
    elif family == "blur_creep":
        sigma = 0.10 + 1.05 * tau
        output = gaussian_filter(output, sigma=sigma, mode="reflect")
        magnitude = sigma
    elif family == "bad_pixel_bloom":
        count = int(round((0.001 + 0.018 * tau) * output.size))
        selected = bad_order[:count]
        values = np.where((selected + frame_index) % 2 == 0, 0.10 + 0.05 * tau, 0.78 + 0.15 * tau)
        output.flat[selected] = values
        magnitude = count / output.size
    elif family == "oscillatory_gain":
        phase = 2.0 * np.pi * tau
        gain = 1.0 + 0.20 * np.sin(2.2 * phase + 0.3)
        offset = 0.05 * np.cos(1.3 * phase - 0.2)
        output = gain * output + offset
        magnitude = abs(gain - 1.0) + abs(offset)
    elif family == "compound_aging":
        gain = 1.0 + 0.12 * tau
        output = gain * output + 0.035 * tau * row_pattern + 0.022 * tau * col_pattern
        output = gaussian_filter(output, sigma=0.10 + 0.72 * tau, mode="reflect")
        count = int(round((0.001 + 0.010 * tau) * output.size))
        selected = bad_order[:count]
        output.flat[selected] = np.where((selected + frame_index) % 2 == 0, 0.12, 0.86)
        magnitude = abs(gain - 1.0) + 0.057 * tau + 0.72 * tau + count / output.size
    else:
        raise ValueError(f"unknown drift family: {family}")
    output += rng.normal(0.0, 0.006 + 0.004 * tau, size=output.shape)
    levels = float(2**12 - 1)
    output = np.round(np.clip(output, 0.0, 1.0) * levels) / levels
    return output.astype(np.float32), float(magnitude)


def generate_sequence(sequence_seed: int, drift_family: str, frames: int = 12, size: int = 64) -> IRSequence:
    if drift_family not in ALL_DRIFTS:
        raise ValueError(f"drift family must be one of {ALL_DRIFTS}")
    if frames < 4:
        raise ValueError("a temporal sequence requires at least four frames")
    base = generate_sample(sequence_seed * 17 + 11, "nominal", has_target=False, size=size)
    rng = np.random.default_rng(sequence_seed * 1_000_003 + sum(map(ord, drift_family)))
    has_target = bool(sequence_seed % 2 == 0)
    x0 = float(rng.uniform(10.0, size - 14.0))
    y0 = float(rng.uniform(10.0, size - 14.0))
    vx = float(rng.uniform(0.42, 0.82) * (-1.0 if rng.random() < 0.5 else 1.0))
    vy = float(rng.uniform(-0.28, 0.28))
    row_pattern = rng.normal(0.0, 1.0, size=(size, 1))
    row_pattern -= np.mean(row_pattern)
    row_pattern /= max(float(np.std(row_pattern)), 1e-9)
    col_pattern = rng.normal(0.0, 1.0, size=(1, size))
    col_pattern -= np.mean(col_pattern)
    col_pattern /= max(float(np.std(col_pattern)), 1e-9)
    bad_order = rng.permutation(size * size)
    output_frames: list[IRSample] = []
    magnitudes: list[float] = []
    for index in range(frames):
        tau = index / max(frames - 1, 1)
        image = np.asarray(base.image, dtype=float).copy()
        target_xy: tuple[int, int] | None = None
        target_mask = np.zeros((size, size), dtype=bool)
        if has_target:
            x = float(np.clip(x0 + vx * index, 5.0, size - 6.0))
            y = float(np.clip(y0 + vy * index + 0.35 * np.sin(index * 0.7), 5.0, size - 6.0))
            target_xy = (int(round(x)), int(round(y)))
            target = _spot(size, x, y, sigma=0.72)
            image += base.latent_contrast * target
            target_mask = target >= np.exp(-2.0)
        frame_rng = np.random.default_rng(sequence_seed * 10_000_019 + index * 7919 + sum(map(ord, drift_family)))
        image, magnitude = _sensor_drift(
            image, drift_family, tau, index, frame_rng, row_pattern, col_pattern, bad_order
        )
        output_frames.append(
            IRSample(
                image=image,
                target_mask=target_mask,
                target_xy=target_xy,
                has_target=has_target,
                seed=sequence_seed * 100 + index,
                config=replace(base.config, family=drift_family),
                latent_contrast=base.latent_contrast,
            )
        )
        magnitudes.append(magnitude)
    return IRSequence(sequence_seed, drift_family, tuple(output_frames), tuple(magnitudes))


def temporal_residual_maps(sequence: IRSequence, update_rate: float = 0.12) -> list[np.ndarray]:
    """Causal running-background residual maps; no future frame is used."""

    background = np.asarray(sequence.frames[0].image, dtype=float).copy()
    maps: list[np.ndarray] = []
    for index, frame in enumerate(sequence.frames):
        current = np.asarray(frame.image, dtype=float)
        residual = current - background
        response = gaussian_filter(residual, 0.60) - gaussian_filter(residual, 2.0)
        maps.append(_robust_probability(response, center=2.0, scale=0.82))
        if index == 0:
            background = current.copy()
        else:
            background = (1.0 - update_rate) * background + update_rate * current
    return maps

