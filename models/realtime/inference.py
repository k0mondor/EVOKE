from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import joblib
import numpy as np
from scipy import signal as sp_signal

from models.realtime.types import EEGWindow

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CHECKPOINT = (
    REPO_ROOT
    / "checkpoints"
    / "realtime_mi_relative_bandpower_v1.joblib"
)
EXPECTED_INPUT_CHANNELS = tuple(f"CH{index}" for index in range(1, 9))
DEFAULT_FEATURE_CHANNELS = ("CH1", "CH2", "CH3", "CH8")
DEFAULT_FREQUENCY_BANDS = (
    (8.0, 12.0),
    (12.0, 16.0),
    (16.0, 22.0),
    (22.0, 30.0),
)


@dataclass(slots=True)
class RealtimeInferenceResult:
    label: str
    probabilities: dict[str, float]
    confidence: float
    model_name: str


@dataclass(slots=True)
class CheckpointTemporalSpatialRunner:
    checkpoint_path: Path = field(default_factory=lambda: DEFAULT_CHECKPOINT)
    _classifier: object | None = field(default=None, init=False)
    _labels: tuple[str, ...] = field(default_factory=tuple, init=False)
    _channel_names: tuple[str, ...] = field(default_factory=tuple, init=False)
    _feature_channels: tuple[str, ...] = field(default_factory=tuple, init=False)
    _frequency_bands: tuple[tuple[float, float], ...] = field(
        default_factory=tuple,
        init=False,
    )
    _protocol: dict = field(default_factory=dict, init=False)
    _model_name: str = field(
        default="relative_bandpower_extra_trees",
        init=False,
    )
    _baseline_window_count: int = field(default=3, init=False)
    _task_window_count: int = field(default=3, init=False)
    _baseline_features: list[np.ndarray] = field(default_factory=list, init=False)
    _task_features: list[np.ndarray] = field(default_factory=list, init=False)

    def load(self) -> None:
        if self._classifier is not None:
            return

        if self.checkpoint_path.suffix.lower() not in {".joblib", ".pkl"}:
            raise ValueError(
                "Realtime inference requires a joblib relative-bandpower checkpoint"
            )
        checkpoint = joblib.load(self.checkpoint_path)
        runtime = dict(checkpoint.get("runtime", {}))
        self._labels = tuple(checkpoint["labels"])
        self._channel_names = tuple(
            runtime.get("input_channel_names", EXPECTED_INPUT_CHANNELS)
        )
        self._feature_channels = tuple(
            runtime.get("feature_channel_names", DEFAULT_FEATURE_CHANNELS)
        )
        self._frequency_bands = tuple(
            tuple(float(value) for value in band)
            for band in runtime.get("frequency_bands_hz", DEFAULT_FREQUENCY_BANDS)
        )
        self._baseline_window_count = int(runtime.get("baseline_window_count", 3))
        self._task_window_count = int(runtime.get("task_window_count", 3))
        self._protocol = dict(checkpoint.get("protocol", {}))
        self._protocol["runtime"] = runtime
        self._model_name = str(
            checkpoint.get(
                "model_name",
                "relative_bandpower_extra_trees",
            )
        )
        self._classifier = checkpoint["classifier"]

    @property
    def labels(self) -> tuple[str, ...]:
        self.load()
        return self._labels

    @property
    def protocol(self) -> dict:
        self.load()
        return dict(self._protocol)

    @property
    def requires_raw_window(self) -> bool:
        self.load()
        return True

    @property
    def baseline_window_count(self) -> int:
        self.load()
        return self._baseline_window_count

    @property
    def task_window_count(self) -> int:
        self.load()
        return self._task_window_count

    def reset(self) -> None:
        self._baseline_features.clear()
        self._task_features.clear()

    def calibrate(self, window: EEGWindow) -> RealtimeInferenceResult:
        self.load()
        feature = self._relative_bandpower_window(window)
        self._baseline_features.append(feature)
        self._baseline_features = self._baseline_features[
            -self._baseline_window_count :
        ]
        uniform = 1.0 / len(self._labels)
        probability_map = {label: uniform for label in self._labels}
        return RealtimeInferenceResult(
            label=self._labels[0],
            probabilities=probability_map,
            confidence=uniform,
            model_name=f"{self._model_name}:calibrating",
        )

    def begin_inference(self) -> None:
        self._task_features.clear()

    def predict(self, window: EEGWindow) -> RealtimeInferenceResult | None:
        self.load()
        return self._predict_relative_bandpower(window)

    def _predict_relative_bandpower(
        self,
        window: EEGWindow,
    ) -> RealtimeInferenceResult | None:
        if self._classifier is None:
            raise RuntimeError("Relative-bandpower classifier failed to initialize")
        if len(self._baseline_features) < self._baseline_window_count:
            raise RuntimeError(
                "Relative-bandpower inference requires "
                f"{self._baseline_window_count} calibrated baseline windows"
            )

        self._task_features.append(self._relative_bandpower_window(window))
        self._task_features = self._task_features[-self._task_window_count :]
        if len(self._task_features) < self._task_window_count:
            return None

        baseline = np.stack(self._baseline_features, axis=0).mean(axis=0)
        task = np.stack(self._task_features, axis=0).mean(axis=0)
        feature = (task - baseline)[None, :].astype(np.float32)
        probabilities = np.asarray(
            self._classifier.predict_proba(feature)[0],
            dtype=np.float64,
        )
        probability_map = {
            label: float(probability)
            for label, probability in zip(self._labels, probabilities)
        }
        label = max(probability_map, key=probability_map.get)
        return RealtimeInferenceResult(
            label=label,
            probabilities=probability_map,
            confidence=probability_map[label],
            model_name=self._model_name,
        )

    def _relative_bandpower_window(self, window: EEGWindow) -> np.ndarray:
        if window.sampling_rate != 250:
            raise ValueError(
                f"Expected a 250 Hz window, got {window.sampling_rate} Hz"
            )
        if window.data.shape[1] != 1000:
            raise ValueError(
                f"Expected a 4 s / 1000 sample window, got {window.data.shape}"
            )
        channel_lookup = {
            channel: index
            for index, channel in enumerate(window.channel_names)
        }
        missing = [
            channel
            for channel in self._channel_names
            if channel not in channel_lookup
        ]
        if missing:
            raise ValueError(f"Missing required EEG channels: {missing}")

        ordered = np.stack(
            [
                np.asarray(window.data[channel_lookup[channel]], dtype=np.float64)
                for channel in self._channel_names
            ],
            axis=0,
        )
        ordered -= np.median(ordered, axis=0, keepdims=True)
        feature_indices = [
            self._channel_names.index(channel)
            for channel in self._feature_channels
        ]
        selected = ordered[feature_indices]
        frequencies, psd = sp_signal.welch(
            selected,
            fs=window.sampling_rate,
            axis=1,
            nperseg=500,
            noverlap=250,
        )
        blocks: list[np.ndarray] = []
        for low_hz, high_hz in self._frequency_bands:
            mask = (frequencies >= low_hz) & (frequencies < high_hz)
            power = np.maximum(
                np.trapz(psd[:, mask], frequencies[mask], axis=1),
                1e-12,
            )
            blocks.append(np.log(power))
        return np.concatenate(blocks, axis=0).astype(np.float32)
