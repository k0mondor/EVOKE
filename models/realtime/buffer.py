from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from models.realtime.types import EEGFrameBatch, EEGWindow


@dataclass(slots=True)
class RollingEEGBuffer:
    sampling_rate: int = 250
    window_size_s: float = 4.0
    stride_s: float = 2.0
    retention_s: float = 10.0
    _samples: np.ndarray = field(default_factory=lambda: np.empty((0, 0), dtype=np.float64))
    _channel_names: tuple[str, ...] = field(default_factory=tuple)
    _base_sample_index: int = 0
    _total_samples: int = 0
    _next_window_end: int = 0

    def append(self, batch: EEGFrameBatch) -> list[EEGWindow]:
        if batch.samples.ndim != 2:
            raise ValueError(f"Expected frame batch shaped [samples, channels], got {batch.samples.shape}")
        if batch.sampling_rate != self.sampling_rate:
            raise ValueError(f"Expected sampling rate {self.sampling_rate}, got {batch.sampling_rate}")

        if not self._channel_names:
            self._channel_names = batch.channel_names
            self._samples = np.empty((0, len(batch.channel_names)), dtype=np.float64)
        elif batch.channel_names != self._channel_names:
            raise ValueError("Incoming frame batch channel layout does not match buffer layout")

        self._samples = np.concatenate([self._samples, np.asarray(batch.samples, dtype=np.float64)], axis=0)
        self._total_samples += int(batch.samples.shape[0])
        if self._next_window_end == 0:
            self._next_window_end = self.window_size_samples

        windows: list[EEGWindow] = []
        while self._total_samples >= self._next_window_end:
            start_sample = self._next_window_end - self.window_size_samples
            end_sample = self._next_window_end
            local_start = start_sample - self._base_sample_index
            local_end = end_sample - self._base_sample_index
            window_samples = self._samples[local_start:local_end]
            if window_samples.shape[0] == self.window_size_samples:
                windows.append(
                    EEGWindow(
                        data=np.asarray(window_samples.T, dtype=np.float32),
                        channel_names=self._channel_names,
                        sampling_rate=self.sampling_rate,
                        start_sample=start_sample,
                        end_sample=end_sample,
                        timestamp_ms=batch.timestamp_ms,
                    )
                )
            self._next_window_end += self.stride_samples

        self._trim()
        return windows

    @property
    def window_size_samples(self) -> int:
        return int(round(self.window_size_s * self.sampling_rate))

    @property
    def stride_samples(self) -> int:
        return int(round(self.stride_s * self.sampling_rate))

    @property
    def retention_samples(self) -> int:
        return max(self.window_size_samples, int(round(self.retention_s * self.sampling_rate)))

    def latest_frame(self, sample_count: int = 72) -> dict[str, list[float]]:
        if self._samples.size == 0:
            return {channel: [] for channel in self._channel_names}
        tail = self._samples[-sample_count:]
        return {
            channel: np.asarray(tail[:, index], dtype=np.float32).tolist()
            for index, channel in enumerate(self._channel_names)
        }

    def reset(self) -> None:
        channel_count = len(self._channel_names)
        self._samples = np.empty((0, channel_count), dtype=np.float64)
        self._base_sample_index = 0
        self._total_samples = 0
        self._next_window_end = 0

    def _trim(self) -> None:
        excess = self._samples.shape[0] - self.retention_samples
        if excess <= 0:
            return
        self._samples = self._samples[excess:]
        self._base_sample_index += excess
