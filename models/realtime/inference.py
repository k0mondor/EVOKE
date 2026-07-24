from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from models.deep.mi_tspnet import TemporalSpatialClassifier, TemporalSpatialEncoder, TemporalSpatialModelConfig
from models.realtime.types import EEGWindow
from models.utils.torch_compat import import_torch

torch = import_torch()
F = torch.nn.functional

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CHECKPOINT = REPO_ROOT / "checkpoints" / "best_long_t_new4_excl133728_plain_cnn.pt"


@dataclass(slots=True)
class RealtimeInferenceResult:
    label: str
    probabilities: dict[str, float]
    confidence: float
    model_name: str


@dataclass(slots=True)
class CheckpointTemporalSpatialRunner:
    checkpoint_path: Path = field(default_factory=lambda: DEFAULT_CHECKPOINT)
    device: str = "cpu"
    _model: TemporalSpatialClassifier | None = field(default=None, init=False)
    _labels: tuple[str, ...] = field(default_factory=tuple, init=False)
    _channel_names: tuple[str, ...] = field(default_factory=tuple, init=False)
    _protocol: dict = field(default_factory=dict, init=False)
    _model_name: str = field(default="plain_cnn", init=False)

    def load(self) -> None:
        if self._model is not None:
            return

        checkpoint = torch.load(str(self.checkpoint_path), map_location=self.device)
        self._labels = tuple(checkpoint["labels"])
        self._channel_names = tuple(checkpoint.get("channel_names", ()))
        self._protocol = dict(checkpoint.get("protocol", {}))
        self._model_name = str(checkpoint.get("model_name", "plain_cnn"))

        config = TemporalSpatialModelConfig(**checkpoint["model_config"])
        encoder = TemporalSpatialEncoder(num_channels=len(self._channel_names), config=config)
        model = TemporalSpatialClassifier(encoder=encoder, config=config)
        model.load_state_dict(checkpoint["state_dict"])
        model.to(self.device)
        model.eval()
        self._model = model

    @property
    def labels(self) -> tuple[str, ...]:
        self.load()
        return self._labels

    @property
    def protocol(self) -> dict:
        self.load()
        return dict(self._protocol)

    def predict(self, window: EEGWindow) -> RealtimeInferenceResult:
        self.load()
        if self._model is None:
            raise RuntimeError("Realtime model failed to initialize")

        features = np.asarray(window.data, dtype=np.float32)[None, ...]
        tensor = torch.tensor(features.tolist(), dtype=torch.float32, device=self.device)
        with torch.no_grad():
            logits = self._model(tensor)
            probabilities = F.softmax(logits, dim=1)[0].detach().cpu().tolist()

        probability_map = {
            label: float(probability)
            for label, probability in zip(self._labels, probabilities)
        }
        label = max(probability_map, key=probability_map.get)
        confidence = probability_map[label]
        return RealtimeInferenceResult(
            label=label,
            probabilities=probability_map,
            confidence=confidence,
            model_name=self._model_name,
        )
