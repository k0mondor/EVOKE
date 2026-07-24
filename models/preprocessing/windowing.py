from dataclasses import dataclass

import numpy as np


@dataclass(slots=True)
class WindowConfig:
    window_size_s: float = 4.0
    stride_s: float = 1.0
    sampling_rate: int = 250
    drop_last: bool = True


@dataclass(slots=True)
class WindowRecord:
    data: np.ndarray
    start_sample: int
    end_sample: int


def build_windows(signal, config: WindowConfig):
    array = np.asarray(signal, dtype=np.float64)
    if array.ndim != 2:
        raise ValueError(f"Expected [samples, channels], got {array.shape}")

    window_samples = int(round(config.window_size_s * config.sampling_rate))
    stride_samples = int(round(config.stride_s * config.sampling_rate))
    if window_samples <= 0 or stride_samples <= 0:
        raise ValueError("window size and stride must be positive")

    records: list[WindowRecord] = []
    start = 0
    limit = array.shape[0] - window_samples
    while start <= limit:
        end = start + window_samples
        records.append(WindowRecord(data=array[start:end], start_sample=start, end_sample=end))
        start += stride_samples

    if not records and not config.drop_last and array.shape[0] > 0:
        records.append(WindowRecord(data=array.copy(), start_sample=0, end_sample=array.shape[0]))
    return records
