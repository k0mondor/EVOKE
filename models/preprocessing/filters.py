from dataclasses import dataclass, field

import numpy as np
from scipy import signal as sp_signal


@dataclass(slots=True)
class FilterConfig:
    low_cut_hz: float = 0.5
    high_cut_hz: float = 40.0
    notch_hz: float = 50.0
    sampling_rate: int = 250
    bandpass_order: int = 4
    notch_quality: float = 30.0
    rereference_mode: str = "average"
    reference_channels: tuple[int, ...] = field(default_factory=tuple)


def _as_2d_array(signal) -> np.ndarray:
    array = np.asarray(signal, dtype=np.float64)
    if array.ndim != 2:
        raise ValueError(f"Expected a 2D EEG array shaped as [samples, channels], got {array.shape}")
    return array


def apply_rereference(signal, config: FilterConfig):
    array = _as_2d_array(signal)
    if config.rereference_mode == "none":
        return array

    if config.reference_channels:
        ref = array[:, list(config.reference_channels)].mean(axis=1, keepdims=True)
    else:
        ref = array.mean(axis=1, keepdims=True)
    return array - ref


def apply_bandpass(signal, config: FilterConfig):
    array = _as_2d_array(signal)
    nyquist = 0.5 * config.sampling_rate
    low = config.low_cut_hz / nyquist
    high = config.high_cut_hz / nyquist
    sos = sp_signal.butter(config.bandpass_order, [low, high], btype="bandpass", output="sos")
    return sp_signal.sosfiltfilt(sos, array, axis=0)


def apply_notch(signal, config: FilterConfig):
    array = _as_2d_array(signal)
    if config.notch_hz <= 0:
        return array

    b, a = sp_signal.iirnotch(
        w0=config.notch_hz,
        Q=config.notch_quality,
        fs=config.sampling_rate,
    )
    return sp_signal.filtfilt(b, a, array, axis=0)
