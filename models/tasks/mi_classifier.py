from dataclasses import dataclass, field
import copy

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from models.datasets.label_mapping import MI_CLASSES


@dataclass(slots=True)
class MIPrediction:
    label: str
    probabilities: dict[str, float] = field(default_factory=dict)


class FrequencyEncoder(nn.Module):
    def __init__(
        self,
        num_channels: int,
        num_bands: int,
        hidden_dim: int = 32,
        embedding_dim: int = 16,
        dropout: float = 0.2,
    ) -> None:
        super().__init__()
        self.embedding_dim = embedding_dim
        self.network = nn.Sequential(
            nn.Flatten(),
            nn.Linear(num_channels * num_bands, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, embedding_dim),
        )

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        return self.network(features)


class FrequencyClassifier(nn.Module):
    def __init__(self, encoder: FrequencyEncoder, num_classes: int, dropout: float = 0.2) -> None:
        super().__init__()
        self.encoder = encoder
        self.head = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(encoder.embedding_dim, num_classes),
        )

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        embedding = self.encoder(features)
        return self.head(embedding)


class MIClassifier:
    def __init__(self, labels: tuple[str, ...] = MI_CLASSES) -> None:
        self.labels = labels
        self.model: FrequencyClassifier | None = None

    def initialize(
        self,
        num_channels: int,
        num_bands: int,
        embedding_dim: int = 16,
        hidden_dim: int = 32,
        dropout: float = 0.2,
    ) -> FrequencyClassifier:
        encoder = FrequencyEncoder(
            num_channels=num_channels,
            num_bands=num_bands,
            hidden_dim=hidden_dim,
            embedding_dim=embedding_dim,
            dropout=dropout,
        )
        self.model = FrequencyClassifier(encoder=encoder, num_classes=len(self.labels), dropout=dropout)
        return self.model

    def fit(
        self,
        train_x: np.ndarray,
        train_y: np.ndarray,
        val_x: np.ndarray | None = None,
        val_y: np.ndarray | None = None,
        epochs: int = 40,
        learning_rate: float = 1e-3,
        weight_decay: float = 5e-4,
        patience: int = 15,
        device: str = "cpu",
    ) -> dict:
        if self.model is None:
            self.initialize(num_channels=train_x.shape[1], num_bands=train_x.shape[2])

        assert self.model is not None
        self.model.to(device)
        optimizer = torch.optim.AdamW(self.model.parameters(), lr=learning_rate, weight_decay=weight_decay)
        criterion = nn.CrossEntropyLoss()

        train_features = torch.tensor(train_x.tolist(), dtype=torch.float32, device=device)
        train_targets = torch.tensor(train_y.tolist(), dtype=torch.long, device=device)
        val_features = None if val_x is None else torch.tensor(val_x.tolist(), dtype=torch.float32, device=device)
        val_targets = None if val_y is None else torch.tensor(val_y.tolist(), dtype=torch.long, device=device)

        history: list[dict[str, float]] = []
        best_state: dict | None = None
        best_entry: dict[str, float] | None = None
        best_val_loss = float("inf")
        epochs_without_improvement = 0
        for epoch_index in range(epochs):
            self.model.train()
            logits = self.model(train_features)
            loss = criterion(logits, train_targets)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            entry = {
                "epoch": float(epoch_index + 1),
                "train_loss": float(loss.item()),
                "train_acc": float((logits.argmax(dim=1) == train_targets).float().mean().item()),
            }
            if val_features is not None and val_targets is not None:
                self.model.eval()
                with torch.no_grad():
                    val_logits = self.model(val_features)
                    entry["val_loss"] = float(criterion(val_logits, val_targets).item())
                    entry["val_acc"] = float((val_logits.argmax(dim=1) == val_targets).float().mean().item())
                if entry["val_loss"] < best_val_loss:
                    best_val_loss = entry["val_loss"]
                    best_state = copy.deepcopy(self.model.state_dict())
                    best_entry = dict(entry)
                    epochs_without_improvement = 0
                else:
                    epochs_without_improvement += 1
            history.append(entry)
            if val_features is not None and val_targets is not None and epochs_without_improvement >= patience:
                break

        if best_state is not None:
            self.model.load_state_dict(best_state)

        if best_entry is not None:
            best_entry["epochs_ran"] = float(len(history))
            return best_entry
        return history[-1] if history else {}

    def predict_proba(self, features: np.ndarray, device: str = "cpu") -> np.ndarray:
        if self.model is None:
            raise RuntimeError("Classifier model is not initialized")

        tensor = torch.tensor(features.tolist(), dtype=torch.float32, device=device)
        self.model.to(device)
        self.model.eval()
        with torch.no_grad():
            logits = self.model(tensor)
            probabilities = F.softmax(logits, dim=1)
        return np.asarray(probabilities.detach().cpu().tolist(), dtype=np.float32)

    def predict(self, window) -> MIPrediction:
        features = np.asarray(window, dtype=np.float32)
        if features.ndim == 2:
            features = features[None, ...]
        probabilities = self.predict_proba(features)[0]
        label_index = int(np.argmax(probabilities))
        return MIPrediction(
            label=self.labels[label_index],
            probabilities={label: float(prob) for label, prob in zip(self.labels, probabilities)},
        )
