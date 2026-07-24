from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from models.preprocessing.filters import FilterConfig, apply_bandpass, apply_notch, apply_rereference
from models.realtime.types import EEGWindow


@dataclass(slots=True)
class OnlinePreprocessor:
    filter_config: FilterConfig = field(
        default_factory=lambda: FilterConfig(
            low_cut_hz=4.0,
            high_cut_hz=30.0,
            notch_hz=50.0,
            sampling_rate=250,
            rereference_mode="none",
        )
    )

    def transform_window(self, window: EEGWindow) -> EEGWindow:
        signal = np.asarray(window.data.T, dtype=np.float64)
        signal = apply_rereference(signal, self.filter_config)
        signal = apply_bandpass(signal, self.filter_config)
        signal = apply_notch(signal, self.filter_config)
        return EEGWindow(
            data=np.asarray(signal.T, dtype=np.float32),
            channel_names=window.channel_names,
            sampling_rate=window.sampling_rate,
            start_sample=window.start_sample,
            end_sample=window.end_sample,
            timestamp_ms=window.timestamp_ms,
        )
