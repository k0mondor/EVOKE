from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(slots=True)
class EEGFrameBatch:
    sampling_rate: int
    channel_names: tuple[str, ...]
    samples: np.ndarray
    timestamp_ms: int
    frame_index: int | None = None
    source: str = "tcp"


@dataclass(slots=True)
class EEGWindow:
    data: np.ndarray
    channel_names: tuple[str, ...]
    sampling_rate: int
    start_sample: int
    end_sample: int
    timestamp_ms: int


@dataclass(slots=True)
class SignalQuality:
    ptp: float
    rms: float
    usable: bool


@dataclass(slots=True)
class TopomapSnapshot:
    id: str
    values: list[float]
    timestamp: str
