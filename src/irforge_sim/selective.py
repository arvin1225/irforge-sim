"""Calibration and post-hoc selective gates for a fixed detector."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler


def _logit(probability: np.ndarray) -> np.ndarray:
    clipped = np.clip(probability, 1e-6, 1.0 - 1e-6)
    return np.log(clipped / (1.0 - clipped))


def _sigmoid(value: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(value, -30.0, 30.0)))


@dataclass(frozen=True)
class TemperatureCalibrator:
    temperature: float

    @classmethod
    def fit(cls, confidences: np.ndarray, correctness: np.ndarray) -> "TemperatureCalibrator":
        logits = _logit(np.asarray(confidences, dtype=float))
        labels = np.asarray(correctness, dtype=float)
        best_temperature, best_nll = 1.0, float("inf")
        for temperature in np.geomspace(0.25, 8.0, 180):
            probabilities = _sigmoid(logits / temperature)
            nll = -np.mean(labels * np.log(probabilities + 1e-9) + (1.0 - labels) * np.log(1.0 - probabilities + 1e-9))
            if nll < best_nll:
                best_nll, best_temperature = float(nll), float(temperature)
        return cls(temperature=best_temperature)

    def transform(self, confidences: np.ndarray | float) -> np.ndarray:
        values = np.atleast_1d(np.asarray(confidences, dtype=float))
        return _sigmoid(_logit(values) / self.temperature)


def acceptance_threshold(risks: np.ndarray, target_coverage: float = 0.8) -> float:
    return float(np.quantile(np.asarray(risks, dtype=float), target_coverage, method="higher"))


class SelectiveRiskGate:
    """Predict detector error from confidence and observable image-quality features."""

    def __init__(self, mode: str = "full", random_state: int = 23) -> None:
        if mode not in {"quality", "no_interactions", "full", "no_bad_pixel", "no_frequency"}:
            raise ValueError(f"unknown gate mode: {mode}")
        self.mode = mode
        self.scaler = StandardScaler()
        self.model = LogisticRegression(C=0.6, class_weight="balanced", max_iter=400, solver="liblinear", random_state=random_state)
        self.constant_risk: float | None = None

    def _design(self, confidence: np.ndarray, quality: np.ndarray) -> np.ndarray:
        confidence = np.asarray(confidence, dtype=float).reshape(-1, 1)
        quality = np.asarray(quality, dtype=float)
        if self.mode == "quality":
            return quality
        if self.mode == "no_bad_pixel":
            quality = quality[:, [0, 1, 2, 4, 5, 6]]
        elif self.mode == "no_frequency":
            quality = quality[:, [0, 1, 2, 3, 6]]
        base = np.concatenate([1.0 - confidence, quality], axis=1)
        if self.mode in {"no_interactions", "no_bad_pixel", "no_frequency"}:
            return base
        interactions = quality * (1.0 - confidence)
        return np.concatenate([base, interactions], axis=1)

    def fit(self, confidence: np.ndarray, quality: np.ndarray, errors: np.ndarray) -> "SelectiveRiskGate":
        x = self._design(confidence, quality)
        y = np.asarray(errors, dtype=int)
        if len(np.unique(y)) < 2:
            self.constant_risk = float(np.mean(y))
            return self
        self.model.fit(self.scaler.fit_transform(x), y)
        return self

    def predict_risk(self, confidence: np.ndarray, quality: np.ndarray) -> np.ndarray:
        x = self._design(confidence, quality)
        if self.constant_risk is not None:
            return np.full(x.shape[0], self.constant_risk, dtype=float)
        return self.model.predict_proba(self.scaler.transform(x))[:, 1]

