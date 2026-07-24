from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from models.realtime.types import SignalQuality


@dataclass(slots=True)
class SignalQualityGate:
    ptp_threshold: float = 179.4873
    rms_threshold: float = 22.4605

    def evaluate(self, window: np.ndarray) -> SignalQuality:
        array = np.asarray(window, dtype=np.float64)
        if array.ndim != 2:
            raise ValueError(f"Expected window shaped [channels, time], got {array.shape}")

        ptp = float(np.ptp(array, axis=1).max())
        rms = float(np.sqrt(np.mean(array**2)))
        usable = ptp <= self.ptp_threshold and rms <= self.rms_threshold
        return SignalQuality(ptp=ptp, rms=rms, usable=usable)
