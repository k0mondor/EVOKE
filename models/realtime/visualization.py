from __future__ import annotations

from datetime import datetime, timezone

import numpy as np

from models.realtime.types import EEGWindow, TopomapSnapshot


def build_topomap_snapshots(window: EEGWindow) -> list[TopomapSnapshot]:
    array = np.asarray(window.data, dtype=np.float64)
    if array.ndim != 2:
        raise ValueError(f"Expected window shaped [channels, time], got {array.shape}")

    instant_source = array[:, -1]
    temporal_mean_source = np.sqrt(np.mean(array**2, axis=1))
    timestamp = datetime.fromtimestamp(window.timestamp_ms / 1000.0, tz=timezone.utc).isoformat()

    return [
        TopomapSnapshot(id="instant", values=_normalize_channels(instant_source), timestamp=timestamp),
        TopomapSnapshot(id="temporal_mean", values=_normalize_channels(temporal_mean_source), timestamp=timestamp),
    ]


def _normalize_channels(values: np.ndarray) -> list[float]:
    source = np.asarray(values, dtype=np.float64)
    if source.size == 0:
        return []

    centered = source - float(np.mean(source))
    scale = float(np.max(np.abs(centered)))
    if scale > 1e-9:
        centered = centered / scale
    return np.asarray(centered, dtype=np.float32).tolist()
