"""Deterministic LWIR-like image formation with factor-controlled degradation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import gaussian_filter

from .config import ShiftConfig, sample_shift


@dataclass(frozen=True)
class IRSample:
    image: np.ndarray
    target_mask: np.ndarray
    target_xy: tuple[int, int] | None
    has_target: bool
    seed: int
    config: ShiftConfig
    latent_contrast: float


def planck_radiance(wavelength_m: np.ndarray | float, temperature_k: float) -> np.ndarray:
    """Spectral radiance from Planck's law in SI units."""

    wavelength = np.asarray(wavelength_m, dtype=np.float64)
    h = 6.62607015e-34
    c = 299792458.0
    k = 1.380649e-23
    exponent = h * c / (wavelength * k * temperature_k)
    return (2.0 * h * c**2) / (wavelength**5 * np.expm1(exponent))


def band_radiance(temperature_k: float) -> float:
    wavelengths = np.linspace(8e-6, 12e-6, 33)
    return float(np.trapezoid(planck_radiance(wavelengths, temperature_k), wavelengths))


def _normalize(array: np.ndarray) -> np.ndarray:
    low, high = np.percentile(array, [1.0, 99.0])
    return np.clip((array - low) / max(1e-8, high - low), 0.0, 1.0)


def _background(size: int, kind: str, strength: float, rng: np.random.Generator) -> np.ndarray:
    fine = gaussian_filter(rng.normal(size=(size, size)), 0.7)
    medium = gaussian_filter(rng.normal(size=(size, size)), 2.2)
    coarse = gaussian_filter(rng.normal(size=(size, size)), 7.0)
    field = 0.23 * fine + 0.48 * medium + 0.76 * coarse
    yy, xx = np.mgrid[0:size, 0:size]

    if kind == "horizon":
        horizon = size * rng.uniform(0.35, 0.7)
        field += 0.7 * np.tanh((yy - horizon) / rng.uniform(2.0, 5.0))
        field += 0.12 * np.sin(xx / rng.uniform(4.0, 9.0))
    elif kind == "sea":
        field += 0.24 * np.sin(yy * rng.uniform(0.6, 1.1) + 0.15 * np.sin(xx / 5.0))
        field += 0.11 * np.sin(yy * rng.uniform(1.6, 2.4))
    elif kind == "urban":
        for _ in range(int(rng.integers(4, 9))):
            x0, y0 = int(rng.integers(0, size - 8)), int(rng.integers(0, size - 8))
            width, height = int(rng.integers(4, 18)), int(rng.integers(3, 15))
            field[y0 : min(size, y0 + height), x0 : min(size, x0 + width)] += rng.uniform(-0.8, 0.9)
        field = gaussian_filter(field, 0.55)
    else:
        field += 0.25 * np.sin(xx / 9.0 + yy / 13.0)

    normalized = _normalize(field)
    return np.clip(0.30 + strength * (normalized - 0.5) * 2.0, 0.02, 0.78)


def _gaussian_spot(size: int, x: float, y: float, sigma: float) -> np.ndarray:
    yy, xx = np.mgrid[0:size, 0:size]
    return np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2.0 * sigma**2))


def generate_sample(
    seed: int,
    family: str = "nominal",
    *,
    has_target: bool | None = None,
    size: int = 64,
    force_zero_contrast: bool = False,
) -> IRSample:
    """Generate one replayable sample; labels never affect the sampled degradation."""

    rng = np.random.default_rng(seed)
    config = sample_shift(family, rng)
    if has_target is None:
        has_target = bool(seed % 2 == 0)

    image = _background(size, config.background, config.clutter_strength, rng)
    background_temperature = float(rng.uniform(282.0, 302.0))
    delta_k = 0.0 if force_zero_contrast else config.target_delta_k
    radiance_background = band_radiance(background_temperature)
    radiance_target = band_radiance(background_temperature + delta_k)
    radiance_ratio = (radiance_target - radiance_background) / max(radiance_background, 1e-12)
    # The band-radiance ratio is converted to the simulator's normalized
    # detector-response scale. This fixed gain is not a camera calibration; it
    # sets nominal targets in the measurable regime so composed degradations,
    # rather than a broken source-domain baseline, determine failure.
    latent_contrast = float(np.clip(4.5 * radiance_ratio * config.transmission, 0.0, 0.70))

    target_xy: tuple[int, int] | None = None
    target_mask = np.zeros((size, size), dtype=bool)
    if has_target:
        x = int(rng.integers(7, size - 7))
        y = int(rng.integers(7, size - 7))
        target_xy = (x, y)
        intrinsic_sigma = float(rng.uniform(0.42, 0.78))
        spot = _gaussian_spot(size, x, y, intrinsic_sigma)
        image += latent_contrast * spot
        target_mask = spot >= np.exp(-2.0)

    distractors = int(rng.poisson(config.distractor_rate))
    for _ in range(distractors):
        x, y = rng.uniform(2, size - 2, size=2)
        sigma = float(rng.uniform(0.35, 1.3))
        amplitude = float(rng.uniform(0.015, 0.09) * (1.0 + config.clutter_strength))
        image += amplitude * _gaussian_spot(size, x, y, sigma)

    image = gaussian_filter(image, config.blur_sigma, mode="reflect")

    row_gain = rng.normal(0.0, config.fpn_gain, size=(size, 1))
    col_gain = rng.normal(0.0, config.fpn_gain * 0.7, size=(1, size))
    row_offset = rng.normal(0.0, config.fpn_offset, size=(size, 1))
    col_offset = rng.normal(0.0, config.fpn_offset * 0.7, size=(1, size))
    image = image * (1.0 + row_gain + col_gain) + row_offset + col_offset

    electrons = np.clip(image, 0.0, 1.0) * config.shot_electrons
    image = rng.poisson(electrons).astype(np.float64) / config.shot_electrons
    image += rng.normal(0.0, config.read_noise, size=image.shape)

    bad_count = int(round(config.bad_pixel_fraction * size * size))
    if bad_count:
        bad_indices = rng.choice(size * size, size=bad_count, replace=False)
        bad_values = rng.choice([0.0, 1.0], size=bad_count).astype(float)
        # Some defects are obvious dead/hot pixels and some are only partially
        # defective. The common detector preprocessor can mask the former; the
        # latter remain a registered stressor.
        partial = rng.random(bad_count) < 0.45
        bad_values[partial & (bad_values > 0.5)] = rng.uniform(0.72, 0.96, size=np.sum(partial & (bad_values > 0.5)))
        bad_values[partial & (bad_values <= 0.5)] = rng.uniform(0.02, 0.16, size=np.sum(partial & (bad_values <= 0.5)))
        image.flat[bad_indices] = bad_values

    levels = float(2**config.quantization_bits - 1)
    image = np.round(np.clip(image, 0.0, 1.0) * levels) / levels
    return IRSample(
        image=image.astype(np.float32),
        target_mask=target_mask,
        target_xy=target_xy,
        has_target=bool(has_target),
        seed=int(seed),
        config=config,
        latent_contrast=latent_contrast,
    )


def generate_family(family: str, seed_start: int, count: int) -> list[IRSample]:
    return [generate_sample(seed_start + index, family) for index in range(count)]
