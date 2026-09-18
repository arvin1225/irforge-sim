"""Registered degradation families for the IRForge synthetic benchmark."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np


TRAIN_FAMILIES = (
    "nominal",
    "blur_only",
    "noise_only",
    "attenuation_only",
    "badpixel_only",
    "clutter_only",
)

CONFIRMATORY_FAMILIES = (
    "blur_noise",
    "attenuation_contrast",
    "badpixel_fpn",
    "clutter_blur",
    "triple_shift",
)

ALL_FAMILIES = TRAIN_FAMILIES + CONFIRMATORY_FAMILIES


@dataclass(frozen=True)
class ShiftConfig:
    """Image-formation parameters; values are controlled surrogates, not a device fit."""

    family: str
    background: str = "cloud"
    target_delta_k: float = 7.0
    distance_km: float = 2.0
    extinction_per_km: float = 0.08
    blur_sigma: float = 0.65
    read_noise: float = 0.012
    shot_electrons: float = 3600.0
    fpn_gain: float = 0.006
    fpn_offset: float = 0.006
    bad_pixel_fraction: float = 0.0005
    clutter_strength: float = 0.16
    distractor_rate: float = 0.5
    quantization_bits: int = 12

    @property
    def transmission(self) -> float:
        return float(np.exp(-self.extinction_per_km * self.distance_km))

    def as_dict(self) -> dict[str, float | str | int]:
        return asdict(self)


def _u(rng: np.random.Generator, low: float, high: float) -> float:
    return float(rng.uniform(low, high))


def sample_shift(family: str, rng: np.random.Generator) -> ShiftConfig:
    """Sample a registered family without using labels or evaluation outcomes."""

    if family not in ALL_FAMILIES:
        raise ValueError(f"unknown degradation family: {family}")
    background = ("cloud", "horizon", "sea", "urban")[int(rng.integers(0, 4))]
    base = dict(
        family=family,
        background=background,
        target_delta_k=_u(rng, 5.8, 9.5),
        distance_km=_u(rng, 1.2, 3.2),
        extinction_per_km=_u(rng, 0.045, 0.095),
        blur_sigma=_u(rng, 0.45, 0.8),
        read_noise=_u(rng, 0.007, 0.015),
        shot_electrons=_u(rng, 3000.0, 5200.0),
        fpn_gain=_u(rng, 0.003, 0.008),
        fpn_offset=_u(rng, 0.003, 0.008),
        bad_pixel_fraction=_u(rng, 0.0, 0.001),
        clutter_strength=_u(rng, 0.10, 0.20),
        distractor_rate=_u(rng, 0.2, 0.8),
        quantization_bits=12,
    )

    if family == "blur_only":
        base["blur_sigma"] = _u(rng, 1.0, 1.55)
    elif family == "noise_only":
        base["read_noise"] = _u(rng, 0.025, 0.052)
        base["shot_electrons"] = _u(rng, 800.0, 1800.0)
    elif family == "attenuation_only":
        base["distance_km"] = _u(rng, 4.5, 7.5)
        base["extinction_per_km"] = _u(rng, 0.12, 0.20)
    elif family == "badpixel_only":
        base["bad_pixel_fraction"] = _u(rng, 0.006, 0.018)
    elif family == "clutter_only":
        base["clutter_strength"] = _u(rng, 0.30, 0.48)
        base["distractor_rate"] = _u(rng, 2.0, 4.5)
    elif family == "blur_noise":
        base["blur_sigma"] = _u(rng, 0.95, 1.55)
        base["read_noise"] = _u(rng, 0.022, 0.050)
        base["shot_electrons"] = _u(rng, 900.0, 1900.0)
    elif family == "attenuation_contrast":
        base["target_delta_k"] = _u(rng, 3.0, 5.6)
        base["distance_km"] = _u(rng, 4.0, 7.0)
        base["extinction_per_km"] = _u(rng, 0.10, 0.18)
    elif family == "badpixel_fpn":
        base["bad_pixel_fraction"] = _u(rng, 0.008, 0.025)
        base["fpn_gain"] = _u(rng, 0.016, 0.045)
        base["fpn_offset"] = _u(rng, 0.014, 0.040)
    elif family == "clutter_blur":
        base["clutter_strength"] = _u(rng, 0.25, 0.45)
        base["distractor_rate"] = _u(rng, 2.0, 5.0)
        base["blur_sigma"] = _u(rng, 0.9, 1.5)
    elif family == "triple_shift":
        base["target_delta_k"] = _u(rng, 3.5, 6.0)
        base["distance_km"] = _u(rng, 3.5, 6.5)
        base["extinction_per_km"] = _u(rng, 0.10, 0.18)
        base["blur_sigma"] = _u(rng, 0.95, 1.5)
        base["read_noise"] = _u(rng, 0.020, 0.050)
        base["shot_electrons"] = _u(rng, 850.0, 1800.0)
        base["clutter_strength"] = _u(rng, 0.22, 0.38)
        base["distractor_rate"] = _u(rng, 1.5, 3.8)

    return ShiftConfig(**base)
