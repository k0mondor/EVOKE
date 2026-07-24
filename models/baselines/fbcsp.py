from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import linalg
from scipy import signal as sp_signal
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis


@dataclass(slots=True)
class FBCSPConfig:
    frequency_bands: tuple[tuple[float, float], ...] = (
        (8.0, 12.0),
        (12.0, 16.0),
        (16.0, 22.0),
        (22.0, 30.0),
    )
    n_components: int = 4
    sampling_rate: int = 500
    bandpass_order: int = 4


def _bandpass_trials(trials: np.ndarray, low_hz: float, high_hz: float, sampling_rate: int, order: int) -> np.ndarray:
    nyquist = 0.5 * sampling_rate
    sos = sp_signal.butter(order, [low_hz / nyquist, high_hz / nyquist], btype="bandpass", output="sos")
    filtered = sp_signal.sosfiltfilt(sos, trials, axis=2)
    return np.asarray(filtered, dtype=np.float64)


def _covariance(trial: np.ndarray) -> np.ndarray:
    cov = trial @ trial.T
    trace = np.trace(cov)
    if trace <= 1e-12:
        return np.eye(trial.shape[0], dtype=np.float64)
    return cov / trace


def _fit_binary_csp(class_a: np.ndarray, class_b: np.ndarray, n_components: int) -> np.ndarray:
    cov_a = np.mean(np.stack([_covariance(trial) for trial in class_a], axis=0), axis=0)
    cov_b = np.mean(np.stack([_covariance(trial) for trial in class_b], axis=0), axis=0)
    composite = cov_a + cov_b
    eigenvalues, eigenvectors = linalg.eigh(composite)
    eigenvalues = np.maximum(eigenvalues, 1e-12)
    whitening = eigenvectors @ np.diag(1.0 / np.sqrt(eigenvalues)) @ eigenvectors.T
    s_a = whitening @ cov_a @ whitening.T
    eigvals_a, eigvecs_a = linalg.eigh(s_a)
    order = np.argsort(eigvals_a)[::-1]
    eigvecs_a = eigvecs_a[:, order]
    filters = eigvecs_a.T @ whitening
    half = max(1, n_components // 2)
    selected = np.concatenate([filters[:half], filters[-half:]], axis=0)
    return np.asarray(selected, dtype=np.float64)


def _logvar_features(trials: np.ndarray, filters: np.ndarray) -> np.ndarray:
    projected = np.einsum("fc,nct->nft", filters, trials)
    var = np.var(projected, axis=2)
    var = np.maximum(var, 1e-12)
    var = var / np.maximum(var.sum(axis=1, keepdims=True), 1e-12)
    return np.log(var)


class FBCSPPipeline:
    """
    Placeholder interface for the classical MI baseline.

    The final implementation should:
    - filter trials into multiple bands
    - fit CSP per band
    - extract log-variance features
    - feed features into an LDA/SVM classifier
    """

    def __init__(self, config: FBCSPConfig | None = None) -> None:
        self.config = config or FBCSPConfig()
        self.classifiers: dict[int, LinearDiscriminantAnalysis] = {}
        self.filters_: dict[tuple[int, tuple[float, float]], np.ndarray] = {}
        self.classes_: np.ndarray | None = None

    def _extract_features(self, trials: np.ndarray, labels: np.ndarray | None = None, fit: bool = False) -> np.ndarray:
        trials = np.asarray(trials, dtype=np.float64)
        if trials.ndim != 3:
            raise ValueError(f"Expected trials shaped [N, C, T], got {trials.shape}")

        feature_blocks: list[np.ndarray] = []
        classes = self.classes_ if self.classes_ is not None else (np.unique(labels) if labels is not None else None)
        if classes is None:
            raise RuntimeError("Classes are not initialized for FBCSP extraction")

        for band in self.config.frequency_bands:
            filtered = _bandpass_trials(
                trials,
                low_hz=band[0],
                high_hz=band[1],
                sampling_rate=self.config.sampling_rate,
                order=self.config.bandpass_order,
            )
            for class_index in classes:
                key = (int(class_index), band)
                if fit:
                    assert labels is not None
                    positive = filtered[labels == class_index]
                    negative = filtered[labels != class_index]
                    if len(positive) == 0 or len(negative) == 0:
                        raise RuntimeError(f"Cannot fit CSP for class {class_index}: insufficient samples")
                    self.filters_[key] = _fit_binary_csp(positive, negative, self.config.n_components)
                filters = self.filters_[key]
                feature_blocks.append(_logvar_features(filtered, filters))

        return np.concatenate(feature_blocks, axis=1)

    def fit(self, train_x, train_y):
        train_x = np.asarray(train_x, dtype=np.float64)
        train_y = np.asarray(train_y, dtype=np.int64)
        self.classes_ = np.unique(train_y)
        features = self._extract_features(train_x, train_y, fit=True)
        self.classifiers = {}
        for class_index in self.classes_:
            binary_target = (train_y == class_index).astype(np.int64)
            classifier = LinearDiscriminantAnalysis()
            classifier.fit(features, binary_target)
            self.classifiers[int(class_index)] = classifier
        return {
            "status": "ok",
            "num_classes": int(len(self.classes_)),
            "num_features": int(features.shape[1]),
        }

    def predict(self, x):
        probabilities = self.predict_proba(x)
        return np.argmax(probabilities, axis=1)

    def predict_proba(self, x) -> np.ndarray:
        if self.classes_ is None or not self.classifiers:
            raise RuntimeError("FBCSP pipeline is not fitted")
        x = np.asarray(x, dtype=np.float64)
        features = self._extract_features(x, fit=False)
        outputs = []
        for class_index in self.classes_:
            classifier = self.classifiers[int(class_index)]
            outputs.append(classifier.predict_proba(features)[:, 1])
        stacked = np.stack(outputs, axis=1)
        stacked = np.maximum(stacked, 1e-8)
        return stacked / stacked.sum(axis=1, keepdims=True)
