from __future__ import annotations

from dataclasses import dataclass
from math import gcd

import numpy as np
from scipy import signal as sp_signal

from models.realtime.types import EEGFrameBatch


@dataclass(slots=True)
class FrameResampler:
    target_sampling_rate: int = 250

    def resample(self, batch: EEGFrameBatch) -> EEGFrameBatch:
        if batch.sampling_rate == self.target_sampling_rate:
            return batch

        source_rate = batch.sampling_rate
        factor = gcd(source_rate, self.target_sampling_rate)
        up = self.target_sampling_rate // factor
        down = source_rate // factor
        samples = sp_signal.resample_poly(np.asarray(batch.samples, dtype=np.float64), up=up, down=down, axis=0)
        return EEGFrameBatch(
            sampling_rate=self.target_sampling_rate,
            channel_names=batch.channel_names,
            samples=np.asarray(samples, dtype=np.float32),
            timestamp_ms=batch.timestamp_ms,
            frame_index=batch.frame_index,
            source=batch.source,
        )
