from __future__ import annotations

from dataclasses import dataclass, field

from models.preprocessing.filters import FilterConfig
from models.realtime.buffer import RollingEEGBuffer
from models.realtime.controller import DeviceActionController, DeviceControlDecision
from models.realtime.inference import CheckpointTemporalSpatialRunner, RealtimeInferenceResult
from models.realtime.online_preprocessor import OnlinePreprocessor
from models.realtime.postprocess import ProbabilitySmoother
from models.realtime.quality import SignalQualityGate
from models.realtime.resampler import FrameResampler
from models.realtime.types import EEGFrameBatch, EEGWindow, SignalQuality, TopomapSnapshot
from models.realtime.visualization import build_topomap_snapshots


@dataclass(slots=True)
class WindowInferenceEvent:
    window: EEGWindow
    quality: SignalQuality
    prediction: RealtimeInferenceResult
    device_action: DeviceControlDecision
    topomaps: list[TopomapSnapshot]


@dataclass(slots=True)
class RealtimeSessionOutput:
    eeg_frame: EEGFrameBatch
    waveform_channels: dict[str, list[float]]
    events: list[WindowInferenceEvent] = field(default_factory=list)


@dataclass(slots=True)
class RealtimeSession:
    resampler: FrameResampler = field(default_factory=lambda: FrameResampler(target_sampling_rate=250))
    buffer: RollingEEGBuffer = field(default_factory=lambda: RollingEEGBuffer(sampling_rate=250))
    preprocessor: OnlinePreprocessor = field(
        default_factory=lambda: OnlinePreprocessor(
            filter_config=FilterConfig(
                low_cut_hz=4.0,
                high_cut_hz=30.0,
                notch_hz=50.0,
                sampling_rate=250,
                rereference_mode="none",
            )
        )
    )
    quality_gate: SignalQualityGate = field(default_factory=SignalQualityGate)
    runner: CheckpointTemporalSpatialRunner = field(default_factory=CheckpointTemporalSpatialRunner)
    smoother: ProbabilitySmoother = field(default_factory=ProbabilitySmoother)
    controller: DeviceActionController = field(default_factory=DeviceActionController)

    def __post_init__(self) -> None:
        protocol = self.runner.protocol
        thresholds = protocol.get("artifact_thresholds", {})
        if thresholds:
            self.quality_gate = SignalQualityGate(
                ptp_threshold=float(thresholds.get("ptp_threshold", self.quality_gate.ptp_threshold)),
                rms_threshold=float(thresholds.get("rms_threshold", self.quality_gate.rms_threshold)),
            )

    def push_frame(self, frame: EEGFrameBatch) -> RealtimeSessionOutput:
        resampled = self.resampler.resample(frame)
        windows = self.buffer.append(resampled)
        events: list[WindowInferenceEvent] = []

        for raw_window in windows:
            clean_window = self.preprocessor.transform_window(raw_window)
            quality = self.quality_gate.evaluate(clean_window.data)
            prediction = self.runner.predict(clean_window)
            smoothed_probabilities = self.smoother.smooth(prediction.probabilities)
            dominant_label = max(smoothed_probabilities, key=smoothed_probabilities.get)
            prediction = RealtimeInferenceResult(
                label=dominant_label,
                probabilities=smoothed_probabilities,
                confidence=smoothed_probabilities[dominant_label],
                model_name=prediction.model_name,
            )
            device_action = self.controller.decide(
                mi_label=prediction.label,
                confidence=prediction.confidence,
                usable=quality.usable,
                timestamp_ms=clean_window.timestamp_ms,
            )
            events.append(
                WindowInferenceEvent(
                    window=clean_window,
                    quality=quality,
                    prediction=prediction,
                    device_action=device_action,
                    topomaps=build_topomap_snapshots(clean_window),
                )
            )

        return RealtimeSessionOutput(
            eeg_frame=resampled,
            waveform_channels=self.buffer.latest_frame(),
            events=events,
        )
