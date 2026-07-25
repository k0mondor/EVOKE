from __future__ import annotations

from dataclasses import dataclass, field

from models.preprocessing.filters import FilterConfig
from models.realtime.buffer import RollingEEGBuffer
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
    transition_guard_s: float = 1.0
    _phase: str | None = field(default=None, init=False)
    _guard_samples_remaining: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        protocol = self.runner.protocol
        thresholds = protocol.get("artifact_thresholds", {})
        if thresholds:
            self.quality_gate = SignalQualityGate(
                ptp_threshold=float(thresholds.get("ptp_threshold", self.quality_gate.ptp_threshold)),
                rms_threshold=float(thresholds.get("rms_threshold", self.quality_gate.rms_threshold)),
            )

    @property
    def required_collection_windows(self) -> int:
        return self.runner.baseline_window_count

    def begin_inference(self) -> None:
        # Drop the overlapping rest/task samples so the first inference window
        # is composed entirely of post-cue data.
        self.buffer.reset()
        self.runner.begin_inference()
        self.smoother.reset()
        self._phase = "inferring"
        self._guard_samples_remaining = int(
            round(self.transition_guard_s * self.buffer.sampling_rate)
        )

    def push_frame(
        self,
        frame: EEGFrameBatch,
        phase: str = "inferring",
    ) -> RealtimeSessionOutput:
        resampled = self.resampler.resample(frame)
        if phase in {"collecting", "inferring"} and phase != self._phase:
            self.buffer.reset()
            self._phase = phase
            self._guard_samples_remaining = int(
                round(self.transition_guard_s * self.buffer.sampling_rate)
            )

        buffered_frame = resampled
        if self._guard_samples_remaining > 0:
            skipped = min(
                self._guard_samples_remaining,
                int(resampled.samples.shape[0]),
            )
            self._guard_samples_remaining -= skipped
            buffered_frame = EEGFrameBatch(
                sampling_rate=resampled.sampling_rate,
                channel_names=resampled.channel_names,
                samples=resampled.samples[skipped:],
                timestamp_ms=resampled.timestamp_ms,
                frame_index=resampled.frame_index,
                source=resampled.source,
            )
        windows = (
            self.buffer.append(buffered_frame)
            if buffered_frame.samples.shape[0] > 0
            else []
        )
        events: list[WindowInferenceEvent] = []

        for raw_window in windows:
            clean_window = self.preprocessor.transform_window(raw_window)
            quality = self.quality_gate.evaluate(clean_window.data)
            model_window = raw_window if self.runner.requires_raw_window else clean_window
            if phase == "collecting":
                prediction = self.runner.calibrate(model_window)
            elif phase == "inferring":
                prediction = self.runner.predict(model_window)
                if prediction is None:
                    continue
            else:
                continue
            smoothed_probabilities = self.smoother.smooth(prediction.probabilities)
            dominant_label = max(smoothed_probabilities, key=smoothed_probabilities.get)
            prediction = RealtimeInferenceResult(
                label=dominant_label,
                probabilities=smoothed_probabilities,
                confidence=smoothed_probabilities[dominant_label],
                model_name=prediction.model_name,
            )
            events.append(
                WindowInferenceEvent(
                    window=clean_window,
                    quality=quality,
                    prediction=prediction,
                    topomaps=build_topomap_snapshots(clean_window),
                )
            )

        return RealtimeSessionOutput(
            eeg_frame=resampled,
            waveform_channels=self.buffer.latest_frame(),
            events=events,
        )
