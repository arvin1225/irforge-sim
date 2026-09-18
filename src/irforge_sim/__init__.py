"""IRForge-Sim: controlled infrared sensor-shift simulation and evaluation."""

from .config import CONFIRMATORY_FAMILIES, TRAIN_FAMILIES, ShiftConfig, sample_shift
from .image_formation import IRSample, generate_sample

__all__ = [
    "CONFIRMATORY_FAMILIES",
    "TRAIN_FAMILIES",
    "IRSample",
    "ShiftConfig",
    "generate_sample",
    "sample_shift",
]

__version__ = "0.2.0"
