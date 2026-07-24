from typing import Literal

from pydantic import BaseModel, Field


class Envelope(BaseModel):
    version: str = "1.0"
    type: str
    session_id: str | None = None
    timestamp_ms: int
    payload: dict | list


class EEGFramePayload(BaseModel):
    sampling_rate: int
    channels: dict[str, list[float]]


class MIPredictionPayload(BaseModel):
    label: Literal["left", "right", "feet"]
    signal_code: Literal[0, 1, 2]
    probabilities: dict[str, float] = Field(default_factory=dict)
    confidence: float
    usable: bool
    model_name: str


class DeviceControlPayload(BaseModel):
    device_id: str
    action: str
    accepted: bool
    reason: str
    signal_code: Literal[0, 1, 2] | None = None


class SignalQualityPayload(BaseModel):
    ptp: float
    rms: float
    usable: bool


class TopomapSnapshotPayload(BaseModel):
    id: Literal["instant", "temporal_mean"]
    values: list[float] = Field(default_factory=list)
    timestamp: str
