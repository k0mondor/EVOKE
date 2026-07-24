from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy import signal as sp_signal


@dataclass(slots=True)
class SpectralConfig:
    sampling_rate: int = 250
    include_relative_power: bool = True
    include_band_ratios: bool = True
    bands: dict[str, tuple[float, float]] = field(
        default_factory=lambda: {
            "delta": (0.5, 4.0),
            "theta": (4.0, 8.0),
            "alpha": (8.0, 13.0),
            "beta": (13.0, 30.0),
            "gamma": (30.0, 40.0),
        }
    )


def compute_psd(window: np.ndarray, sampling_rate: int) -> tuple[np.ndarray, np.ndarray]:
    frequencies, power = sp_signal.welch(
        window,
        fs=sampling_rate,
        axis=0,
        nperseg=min(window.shape[0], sampling_rate * 2),
    )
    return frequencies, power


def bandpower_features(window: np.ndarray, config: SpectralConfig) -> np.ndarray:
    frequencies, power = compute_psd(window, config.sampling_rate)
    feature_rows: list[np.ndarray] = []
    absolute_bandpowers: list[np.ndarray] = []
    for low_hz, high_hz in config.bands.values():
        mask = (frequencies >= low_hz) & (frequencies < high_hz)
        if not np.any(mask):
            bandpower = np.zeros(power.shape[1], dtype=np.float64)
            absolute_bandpowers.append(bandpower)
            feature_rows.append(bandpower)
            continue
        bandpower = np.trapz(power[mask], frequencies[mask], axis=0)
        absolute_bandpowers.append(bandpower)
        feature_rows.append(bandpower)

    absolute = np.stack(absolute_bandpowers, axis=0)
    total = np.maximum(absolute.sum(axis=0, keepdims=True), 1e-12)
    if config.include_relative_power:
        feature_rows.extend(list(absolute / total))

    if config.include_band_ratios:
        band_names = list(config.bands.keys())
        band_to_values = {name: absolute[idx] for idx, name in enumerate(band_names)}
        eps = 1e-8
        ratio_pairs = [
            ("theta", "alpha"),
            ("theta", "beta"),
            ("alpha", "beta"),
        ]
        for numerator, denominator in ratio_pairs:
            if numerator in band_to_values and denominator in band_to_values:
                feature_rows.append(band_to_values[numerator] / (band_to_values[denominator] + eps))

    features = np.stack(feature_rows, axis=0).T
    return np.log1p(features)


def batch_bandpower_features(windows: list[np.ndarray], config: SpectralConfig) -> np.ndarray:
    return np.stack([bandpower_features(window, config) for window in windows], axis=0)


def normalize_features(train_features: np.ndarray, eval_features: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mean = train_features.mean(axis=0, keepdims=True)
    std = train_features.std(axis=0, keepdims=True) + 1e-6
    return (train_features - mean) / std, (eval_features - mean) / std
