"""Classical and lightweight learned infrared small-target detectors."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import gaussian_filter, laplace, maximum_filter, median_filter
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.preprocessing import StandardScaler

from .image_formation import IRSample


@dataclass(frozen=True)
class DetectionResult:
    score_map: np.ndarray
    threshold: float
    peaks_xy: tuple[tuple[int, int], ...]
    top_xy: tuple[int, int]
    top_score: float
    predicted_present: bool
    localized: bool
    false_alarms: int
    correct: bool
    raw_confidence: float


def _sigmoid(value: np.ndarray | float) -> np.ndarray:
    clipped = np.clip(value, -30.0, 30.0)
    return 1.0 / (1.0 + np.exp(-clipped))


def _robust_probability(response: np.ndarray, center: float = 2.5, scale: float = 0.9) -> np.ndarray:
    median = float(np.median(response))
    mad = float(np.median(np.abs(response - median)))
    robust_z = (response - median) / max(1e-5, 1.4826 * mad)
    return _sigmoid((robust_z - center) / scale).astype(np.float32)


def sanitize_image(image: np.ndarray) -> np.ndarray:
    """Apply a fixed dead/hot-pixel mask, leaving partial defects untouched."""

    cleaned = np.asarray(image, dtype=np.float32).copy()
    obvious = (cleaned <= 1e-5) | (cleaned >= 1.0 - 1e-5)
    if np.any(obvious):
        replacement = median_filter(cleaned, size=3, mode="reflect")
        cleaned[obvious] = replacement[obvious]
    return cleaned


def local_contrast_map(image: np.ndarray) -> np.ndarray:
    image = sanitize_image(image)
    responses = []
    for small, large in ((0.55, 1.8), (0.85, 2.7), (1.2, 4.0)):
        responses.append(gaussian_filter(image, small) - gaussian_filter(image, large))
    return _robust_probability(np.maximum.reduce(responses), center=2.35, scale=0.85)


def matched_filter_map(image: np.ndarray) -> np.ndarray:
    image = sanitize_image(image)
    local_mean = gaussian_filter(image, 3.2)
    local_energy = gaussian_filter((image - local_mean) ** 2, 3.2)
    numerator = gaussian_filter(image, 0.75) - local_mean
    response = numerator / np.sqrt(np.maximum(local_energy, 1e-6))
    return _robust_probability(response, center=2.15, scale=0.8)


def pixel_features(image: np.ndarray) -> np.ndarray:
    image = sanitize_image(image)
    blur_06 = gaussian_filter(image, 0.6)
    blur_14 = gaussian_filter(image, 1.4)
    blur_30 = gaussian_filter(image, 3.0)
    dog_small = blur_06 - blur_14
    dog_large = blur_14 - blur_30
    local_var = np.maximum(gaussian_filter(image**2, 2.0) - gaussian_filter(image, 2.0) ** 2, 0.0)
    gy, gx = np.gradient(blur_06)
    features = np.stack(
        [
            image,
            dog_small,
            dog_large,
            dog_small / np.sqrt(local_var + 1e-6),
            np.sqrt(gx**2 + gy**2),
            laplace(blur_06),
            np.sqrt(local_var),
        ],
        axis=-1,
    )
    return features.astype(np.float32)


class LearnedPixelDetector:
    """A small, deterministic learned baseline on fixed physical-scale features."""

    def __init__(self, random_state: int = 17) -> None:
        self.scaler = StandardScaler()
        self.model = HistGradientBoostingClassifier(
            learning_rate=0.07,
            max_iter=100,
            max_leaf_nodes=15,
            min_samples_leaf=24,
            l2_regularization=1.2,
            random_state=random_state,
        )
        self.random_state = random_state
        self.is_fitted = False

    def fit(self, samples: list[IRSample], negatives_per_image: int = 240) -> "LearnedPixelDetector":
        feature_rows: list[np.ndarray] = []
        labels: list[np.ndarray] = []
        rng = np.random.default_rng(self.random_state)
        for sample in samples:
            features = pixel_features(sample.image).reshape(-1, 7)
            mask = sample.target_mask.reshape(-1)
            positive = np.flatnonzero(mask)
            excluded = gaussian_filter(sample.target_mask.astype(float), 1.5).reshape(-1) > 0.02
            negative_pool = np.flatnonzero(~excluded)
            count = min(negatives_per_image, len(negative_pool))
            # Random background alone almost never samples the glints, edges and
            # defective pixels that dominate infrared false alarms. Half of the
            # negatives are therefore deterministic hard negatives from the
            # strongest classical response; this is fixed before confirmation.
            hard_response = local_contrast_map(sample.image).reshape(-1)
            hard_pool = negative_pool[np.argsort(hard_response[negative_pool], kind="stable")[-max(1, count // 2) :]]
            random_count = count - len(hard_pool)
            remaining = np.setdiff1d(negative_pool, hard_pool, assume_unique=False)
            random_negative = rng.choice(remaining, size=random_count, replace=False)
            negative = np.concatenate([hard_pool, random_negative])
            if len(positive):
                feature_rows.append(features[positive])
                labels.append(np.ones(len(positive), dtype=np.int8))
            feature_rows.append(features[negative])
            labels.append(np.zeros(len(negative), dtype=np.int8))
        x = np.concatenate(feature_rows, axis=0)
        y = np.concatenate(labels, axis=0)
        x_scaled = self.scaler.fit_transform(x)
        sample_weight = np.where(y == 1, 5.0, 1.0)
        self.model.fit(x_scaled, y, sample_weight=sample_weight)
        self.is_fitted = True
        return self

    def predict_map(self, image: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("detector must be fitted before prediction")
        features = pixel_features(image)
        probabilities = self.model.predict_proba(self.scaler.transform(features.reshape(-1, 7)))[:, 1]
        return probabilities.reshape(image.shape).astype(np.float32)


def evaluate_score_map(sample: IRSample, score_map: np.ndarray, threshold: float, tolerance: float = 2.5) -> DetectionResult:
    local_maxima = maximum_filter(score_map, size=5, mode="nearest") == score_map
    peak_yx = np.argwhere(local_maxima & (score_map >= threshold))
    peaks = tuple((int(x), int(y)) for y, x in peak_yx)
    top_index = int(np.argmax(score_map))
    top_y, top_x = np.unravel_index(top_index, score_map.shape)
    top_score = float(score_map[top_y, top_x])
    predicted_present = bool(peaks)

    localized = False
    false_alarms = len(peaks)
    if sample.has_target and sample.target_xy is not None:
        tx, ty = sample.target_xy
        distances = [float(np.hypot(x - tx, y - ty)) for x, y in peaks]
        localized = bool(distances and min(distances) <= tolerance)
        false_alarms = int(sum(distance > tolerance for distance in distances))
        correct = localized
    else:
        correct = not predicted_present

    presence_confidence = top_score if predicted_present else 1.0 - top_score
    raw_confidence = float(np.clip(max(0.5, presence_confidence), 0.500001, 0.999999))
    return DetectionResult(
        score_map=score_map,
        threshold=float(threshold),
        peaks_xy=peaks,
        top_xy=(int(top_x), int(top_y)),
        top_score=top_score,
        predicted_present=predicted_present,
        localized=localized,
        false_alarms=false_alarms,
        correct=bool(correct),
        raw_confidence=raw_confidence,
    )


def tune_threshold(samples: list[IRSample], maps: list[np.ndarray]) -> float:
    best_threshold, best_score = 0.5, -1.0
    candidates = np.unique(
        np.concatenate(
            [
                np.linspace(0.25, 0.92, 38),
                np.linspace(0.925, 0.99, 24),
                np.linspace(0.991, 0.9995, 18),
            ]
        )
    )
    for threshold in candidates:
        results = [evaluate_score_map(sample, score_map, float(threshold)) for sample, score_map in zip(samples, maps, strict=True)]
        tp = sum(result.localized for result, sample in zip(results, samples, strict=True) if sample.has_target)
        fn = sum(not result.localized for result, sample in zip(results, samples, strict=True) if sample.has_target)
        fp = sum(result.false_alarms for result in results)
        f1 = 2.0 * tp / max(1.0, 2.0 * tp + fp + fn)
        if f1 > best_score + 1e-12:
            best_score, best_threshold = f1, float(threshold)
    return best_threshold


def image_quality_features(image: np.ndarray) -> np.ndarray:
    smooth = gaussian_filter(image, 1.2)
    residual = image - smooth
    noise_mad = np.median(np.abs(residual - np.median(residual))) * 1.4826
    row_pattern = np.std(np.mean(image, axis=1) - gaussian_filter(np.mean(image, axis=1), 2.0))
    col_pattern = np.std(np.mean(image, axis=0) - gaussian_filter(np.mean(image, axis=0), 2.0))
    extreme_fraction = np.mean((image <= 1e-5) | (image >= 1.0 - 1e-5))
    high_frequency = np.mean(np.abs(residual)) / max(1e-6, np.std(image))
    dog = gaussian_filter(image, 0.6) - gaussian_filter(image, 2.2)
    clutter_peaks = np.mean(dog > np.percentile(dog, 97.5))
    dynamic_range = np.percentile(image, 99) - np.percentile(image, 1)
    return np.array(
        [noise_mad, row_pattern, col_pattern, extreme_fraction, high_frequency, clutter_peaks, dynamic_range],
        dtype=np.float64,
    )


QUALITY_NAMES = (
    "noise_mad",
    "row_pattern",
    "col_pattern",
    "extreme_fraction",
    "high_frequency",
    "clutter_peaks",
    "dynamic_range",
)
