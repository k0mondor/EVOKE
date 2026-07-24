from typing import Literal

from pydantic import BaseModel, Field


class Envelope(BaseModel):
    version: str = "1.0"
    type: str
    session_id: str | None = None
    timestamp_ms: int
    payload: dict


class EEGFramePayload(BaseModel):
    sampling_rate: int
    channels: dict[str, list[float]]


class MIPredictionPayload(BaseModel):
    label: Literal["left", "right", "feet"]
    probabilities: dict[str, float] = Field(default_factory=dict)
    confidence: float


class DeviceControlPayload(BaseModel):
    device_id: str
    action: str
    accepted: bool
