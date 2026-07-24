from __future__ import annotations

from dataclasses import dataclass
import math
import time

import numpy as np

from models.realtime.types import EEGFrameBatch


@dataclass(slots=True)
class MockEEGSource:
    sampling_rate: int = 500
    samples_per_frame: int = 10
    channel_names: tuple[str, ...] = ("CH1", "CH2", "CH3", "CH4", "CH5", "CH6", "CH7", "CH8")
    _tick: int = 0

    def next_frame(self) -> EEGFrameBatch:
        frame = []
        for sample_index in range(self.samples_per_frame):
            t = (self._tick + sample_index) / float(self.sampling_rate)
            frame.append(
                [
                    14.0 * math.sin(2.0 * math.pi * (8.0 + channel_index * 0.3) * t)
                    + 5.5 * math.cos(2.0 * math.pi * (3.5 + channel_index * 0.2) * t)
                    for channel_index in range(len(self.channel_names))
                ]
            )

        self._tick += self.samples_per_frame
        return EEGFrameBatch(
            sampling_rate=self.sampling_rate,
            channel_names=self.channel_names,
            samples=np.asarray(frame, dtype=np.float32),
            timestamp_ms=int(time.time() * 1000),
            frame_index=self._tick // self.samples_per_frame,
            source="demo",
        )
