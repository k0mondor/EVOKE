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
        TopomapSnapshot(id="instant", values=_expand_to_grid(instant_source), timestamp=timestamp),
        TopomapSnapshot(id="temporal_mean", values=_expand_to_grid(temporal_mean_source), timestamp=timestamp),
    ]


def _expand_to_grid(values: np.ndarray, target_size: int = 12) -> list[float]:
    source = np.asarray(values, dtype=np.float64)
    if source.size == 0:
        return [0.0] * target_size
    if source.size == target_size:
        normalized = source
    else:
        x_source = np.linspace(0.0, 1.0, num=source.size)
        x_target = np.linspace(0.0, 1.0, num=target_size)
        normalized = np.interp(x_target, x_source, source)

    scale = float(np.max(np.abs(normalized)))
    if scale > 1e-9:
        normalized = normalized / scale
    return np.asarray(normalized, dtype=np.float32).tolist()
