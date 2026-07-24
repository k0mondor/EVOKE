from dataclasses import dataclass, field


@dataclass(slots=True)
class PipelineStage:
    name: str
    purpose: str


@dataclass(slots=True)
class PipelineDefinition:
    training: list[PipelineStage] = field(default_factory=list)
    realtime: list[PipelineStage] = field(default_factory=list)


PIPELINE = PipelineDefinition(
    training=[
        PipelineStage("raw_input", "Load EEG sessions and label metadata."),
        PipelineStage("preprocessing", "Apply filters, rereference, and ICA."),
        PipelineStage("trial_or_windowing", "Extract labeled left/right/feet trials or fixed-length windows."),
        PipelineStage("baseline_branch", "Train CSP/FBCSP-based classical MI baseline."),
        PipelineStage("model_branch", "Train contrastive encoder and temporal-spatial MI classifier."),
        PipelineStage("evaluation", "Compare baseline and neural model under the same split policy."),
    ],
    realtime=[
        PipelineStage("stream_buffer", "Collect continuous EEG frames."),
        PipelineStage("preprocessing", "Run online filter and artifact pipeline."),
        PipelineStage("windowing", "Build inference windows from the rolling buffer."),
        PipelineStage("inference", "Run MI decoder and estimate left/right/feet probabilities."),
        PipelineStage("transport", "Push results to websocket clients."),
        PipelineStage("device_feedback", "Drive monitor-page and downstream interactive feedback."),
    ],
)
