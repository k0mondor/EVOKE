from dataclasses import dataclass

import numpy as np
from scipy import linalg, signal as sp_signal


@dataclass(slots=True)
class ICAConfig:
    n_components: int | None = None
    random_state: int = 42
    max_iter: int = 300
    tol: float = 1e-4
    max_remove_components: int = 2
    kurtosis_threshold: float = 4.0
    low_frequency_hz: float = 3.0
    low_frequency_ratio_threshold: float = 0.5
    sampling_rate: int = 250
    enabled: bool = True


def _sym_decorrelation(weights: np.ndarray) -> np.ndarray:
    eigenvalues, eigenvectors = linalg.eigh(weights @ weights.T)
    eigenvalues = np.maximum(eigenvalues, 1e-12)
    whitening = eigenvectors @ np.diag(1.0 / np.sqrt(eigenvalues)) @ eigenvectors.T
    return whitening @ weights


def _fast_ica(signal: np.ndarray, config: ICAConfig) -> tuple[np.ndarray, np.ndarray]:
    centered = signal - signal.mean(axis=0, keepdims=True)
    covariance = np.cov(centered, rowvar=False)
    eigenvalues, eigenvectors = linalg.eigh(covariance)
    order = np.argsort(eigenvalues)[::-1]
    eigenvalues = np.maximum(eigenvalues[order], 1e-12)
    eigenvectors = eigenvectors[:, order]

    n_channels = signal.shape[1]
    n_components = min(config.n_components or n_channels, n_channels)
    eigenvalues = eigenvalues[:n_components]
    eigenvectors = eigenvectors[:, :n_components]

    whitening = eigenvectors @ np.diag(1.0 / np.sqrt(eigenvalues))
    whitened = centered @ whitening

    generator = np.random.default_rng(config.random_state)
    weights = generator.standard_normal(size=(n_components, n_components))
    weights = _sym_decorrelation(weights)

    for _ in range(config.max_iter):
        projection = whitened @ weights.T
        g_projection = np.tanh(projection)
        g_derivative = 1.0 - g_projection**2
        updated = (g_projection.T @ whitened) / whitened.shape[0]
        updated -= np.diag(g_derivative.mean(axis=0)) @ weights
        updated = _sym_decorrelation(updated)

        delta = np.max(np.abs(np.abs(np.diag(updated @ weights.T)) - 1.0))
        weights = updated
        if delta < config.tol:
            break

    sources = whitened @ weights.T
    unmixing = weights @ whitening.T
    mixing = linalg.pinv(unmixing)
    return sources, mixing


def _component_scores(sources: np.ndarray, sampling_rate: int, low_frequency_hz: float) -> tuple[np.ndarray, np.ndarray]:
    centered = sources - sources.mean(axis=0, keepdims=True)
    std = centered.std(axis=0, keepdims=True) + 1e-8
    normalized = centered / std
    kurtosis = np.mean(normalized**4, axis=0) - 3.0

    frequencies, power = sp_signal.welch(
        sources,
        fs=sampling_rate,
        axis=0,
        nperseg=min(sampling_rate * 2, sources.shape[0]),
    )
    total_mask = (frequencies >= 0.5) & (frequencies <= 40.0)
    low_mask = (frequencies >= 0.5) & (frequencies <= low_frequency_hz)
    total_power = np.maximum(power[total_mask].sum(axis=0), 1e-12)
    low_ratio = power[low_mask].sum(axis=0) / total_power
    return kurtosis, low_ratio


def run_ica(signal, config: ICAConfig):
    array = np.asarray(signal, dtype=np.float64)
    if not config.enabled or array.ndim != 2 or array.shape[1] < 2:
        return array

    sources, mixing = _fast_ica(array, config)
    kurtosis, low_ratio = _component_scores(sources, config.sampling_rate, config.low_frequency_hz)
    candidate_indices = np.where(
        (np.abs(kurtosis) >= config.kurtosis_threshold)
        | (low_ratio >= config.low_frequency_ratio_threshold)
    )[0]
    if candidate_indices.size == 0:
        return array

    ranked = sorted(
        candidate_indices.tolist(),
        key=lambda idx: (low_ratio[idx], abs(kurtosis[idx])),
        reverse=True,
    )[: config.max_remove_components]
    cleaned_sources = sources.copy()
    cleaned_sources[:, ranked] = 0.0
    reconstructed = cleaned_sources @ mixing.T + array.mean(axis=0, keepdims=True)
    return reconstructed
