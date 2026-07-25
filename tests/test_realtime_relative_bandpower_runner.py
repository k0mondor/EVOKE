from __future__ import annotations

import joblib
import numpy as np
from sklearn.dummy import DummyClassifier

from models.realtime.inference import CheckpointTemporalSpatialRunner
from models.realtime.types import EEGWindow


def _window(amplitude: float, start_sample: int) -> EEGWindow:
    time = np.arange(1000, dtype=np.float64) / 250.0
    data = np.stack(
        [
            amplitude * np.sin(2.0 * np.pi * (9.0 + channel) * time)
            for channel in range(8)
        ],
        axis=0,
    ).astype(np.float32)
    return EEGWindow(
        data=data,
        channel_names=tuple(f"CH{index}" for index in range(1, 9)),
        sampling_rate=250,
        start_sample=start_sample,
        end_sample=start_sample + 1000,
        timestamp_ms=start_sample * 4,
    )


def test_relative_bandpower_runner_calibrates_then_predicts_segment(tmp_path) -> None:
    classifier = DummyClassifier(strategy="prior")
    classifier.fit(
        np.zeros((6, 16), dtype=np.float32),
        np.asarray([0, 1, 1, 2, 2, 2]),
    )
    checkpoint_path = tmp_path / "relative_bandpower.joblib"
    joblib.dump(
        {
            "model_name": "test_relative_bandpower",
            "labels": ["left", "right", "feet"],
            "classifier": classifier,
            "protocol": {},
            "runtime": {
                "input_channel_names": [
                    "CH1",
                    "CH2",
                    "CH3",
                    "CH4",
                    "CH5",
                    "CH6",
                    "CH7",
                    "CH8",
                ],
                "feature_channel_names": ["CH1", "CH2", "CH3", "CH8"],
                "frequency_bands_hz": [
                    [8.0, 12.0],
                    [12.0, 16.0],
                    [16.0, 22.0],
                    [22.0, 30.0],
                ],
                "baseline_window_count": 3,
                "task_window_count": 3,
            },
        },
        checkpoint_path,
    )
    runner = CheckpointTemporalSpatialRunner(checkpoint_path=checkpoint_path)

    assert runner.requires_raw_window is True
    assert runner.baseline_window_count == 3
    for index in range(3):
        calibration = runner.calibrate(_window(1.0, index * 500))
        assert calibration.model_name.endswith(":calibrating")

    runner.begin_inference()
    assert runner.predict(_window(1.2, 2000)) is None
    assert runner.predict(_window(1.2, 2500)) is None
    prediction = runner.predict(_window(1.2, 3000))

    assert prediction is not None
    assert prediction.label == "feet"
    assert prediction.model_name == "test_relative_bandpower"
    assert np.isclose(sum(prediction.probabilities.values()), 1.0)
