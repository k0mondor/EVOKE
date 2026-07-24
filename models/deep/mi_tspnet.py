from __future__ import annotations

from dataclasses import dataclass
import copy

import numpy as np

from models.datasets.label_mapping import MI_CLASSES
from models.utils.torch_compat import import_torch

torch = import_torch()
nn = torch.nn
F = torch.nn.functional


@dataclass(slots=True)
class TemporalSpatialModelConfig:
    num_classes: int = 3
    dropout: float = 0.25
    embedding_dim: int = 64
    temporal_kernel_sizes: tuple[int, ...] = (15, 31, 63)
    temporal_filters: int = 16
    spatial_filters: int = 32
    learning_rate: float = 1e-3
    weight_decay: float = 1e-4
    batch_size: int = 8
    epochs: int = 80
    patience: int = 15
    label_smoothing: float = 0.05


@dataclass(slots=True)
class TemporalSpatialTrainingResult:
    best_epoch: int
    train_loss: float
    train_acc: float
    val_loss: float
    val_acc: float


class SEBlock(nn.Module):
    def __init__(self, channels: int, reduction: int = 4) -> None:
        super().__init__()
        hidden = max(4, channels // reduction)
        self.network = nn.Sequential(
            nn.AdaptiveAvgPool1d(1),
            nn.Conv1d(channels, hidden, kernel_size=1),
            nn.GELU(),
            nn.Conv1d(hidden, channels, kernel_size=1),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x * self.network(x)


class TemporalSpatialEncoder(nn.Module):
    def __init__(
        self,
        num_channels: int,
        config: TemporalSpatialModelConfig,
    ) -> None:
        super().__init__()
        branch_outputs = []
        for kernel_size in config.temporal_kernel_sizes:
            padding = kernel_size // 2
            branch_outputs.append(
                nn.Sequential(
                    nn.Conv1d(num_channels, config.temporal_filters, kernel_size=kernel_size, padding=padding, bias=False),
                    nn.BatchNorm1d(config.temporal_filters),
                    nn.GELU(),
                )
            )
        self.temporal_branches = nn.ModuleList(branch_outputs)
        merged_channels = config.temporal_filters * len(config.temporal_kernel_sizes)
        self.spatial = nn.Sequential(
            nn.Conv1d(merged_channels, config.spatial_filters, kernel_size=1, bias=False),
            nn.BatchNorm1d(config.spatial_filters),
            nn.GELU(),
            nn.Dropout(config.dropout),
            SEBlock(config.spatial_filters),
            nn.AdaptiveAvgPool1d(1),
        )
        self.embedding = nn.Linear(config.spatial_filters, config.embedding_dim)
        self.embedding_dim = config.embedding_dim

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        temporal = torch.cat([branch(x) for branch in self.temporal_branches], dim=1)
        spatial = self.spatial(temporal).squeeze(-1)
        return self.embedding(spatial)


class TemporalSpatialClassifier(nn.Module):
    def __init__(self, encoder: TemporalSpatialEncoder, config: TemporalSpatialModelConfig) -> None:
        super().__init__()
        self.encoder = encoder
        self.head = nn.Sequential(
            nn.GELU(),
            nn.Dropout(config.dropout),
            nn.Linear(config.embedding_dim, config.num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        embedding = self.encoder(x)
        return self.head(embedding)


class TemporalSpatialMIModel:
    """
    Planned main neural model for left/right/feet motor imagery.

    Intended structure:
    - multi-scale temporal convolutions
    - spatial channel mixing
    - channel attention
    - embedding head
    - 3-class classifier
    """

    def __init__(self, config: TemporalSpatialModelConfig | None = None) -> None:
        self.config = config or TemporalSpatialModelConfig()
        self.labels = MI_CLASSES
        self.model: TemporalSpatialClassifier | None = None

    def build(self, num_channels: int) -> TemporalSpatialClassifier:
        encoder = TemporalSpatialEncoder(num_channels=num_channels, config=self.config)
        self.model = TemporalSpatialClassifier(encoder=encoder, config=self.config)
        return self.model

    def fit(
        self,
        train_x: np.ndarray,
        train_y: np.ndarray,
        val_x: np.ndarray | None = None,
        val_y: np.ndarray | None = None,
        device: str = "cpu",
    ) -> dict:
        if train_x.ndim != 3:
            raise ValueError(f"Expected train_x shaped [N, C, T], got {train_x.shape}")
        if self.model is None:
            self.build(num_channels=train_x.shape[1])

        assert self.model is not None
        self.model.to(device)
        optimizer = torch.optim.AdamW(
            self.model.parameters(),
            lr=self.config.learning_rate,
            weight_decay=self.config.weight_decay,
        )
        criterion = nn.CrossEntropyLoss(label_smoothing=self.config.label_smoothing)

        train_features = torch.tensor(train_x.tolist(), dtype=torch.float32, device=device)
        train_targets = torch.tensor(train_y.tolist(), dtype=torch.long, device=device)
        val_features = None if val_x is None else torch.tensor(val_x.tolist(), dtype=torch.float32, device=device)
        val_targets = None if val_y is None else torch.tensor(val_y.tolist(), dtype=torch.long, device=device)

        history: list[dict[str, float]] = []
        best_state: dict | None = None
        best_entry: dict[str, float] | None = None
        best_val_loss = float("inf")
        patience_counter = 0

        for epoch_index in range(self.config.epochs):
            permutation = torch.randperm(train_features.shape[0], device=device)
            batch_losses: list[float] = []
            batch_accs: list[float] = []
            self.model.train()

            for start in range(0, train_features.shape[0], self.config.batch_size):
                indices = permutation[start : start + self.config.batch_size]
                batch_x = train_features[indices]
                batch_y = train_targets[indices]
                logits = self.model(batch_x)
                loss = criterion(logits, batch_y)

                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

                batch_losses.append(float(loss.item()))
                batch_accs.append(float((logits.argmax(dim=1) == batch_y).float().mean().item()))

            entry = {
                "epoch": float(epoch_index + 1),
                "train_loss": float(np.mean(batch_losses) if batch_losses else 0.0),
                "train_acc": float(np.mean(batch_accs) if batch_accs else 0.0),
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
                    patience_counter = 0
                else:
                    patience_counter += 1

            history.append(entry)
            if val_features is not None and val_targets is not None and patience_counter >= self.config.patience:
                break

        if best_state is not None:
            self.model.load_state_dict(best_state)

        return {
            "config": {
                "learning_rate": self.config.learning_rate,
                "weight_decay": self.config.weight_decay,
                "batch_size": self.config.batch_size,
                "epochs": self.config.epochs,
                "patience": self.config.patience,
                "label_smoothing": self.config.label_smoothing,
                "dropout": self.config.dropout,
                "temporal_kernel_sizes": self.config.temporal_kernel_sizes,
                "embedding_dim": self.config.embedding_dim,
            },
            "best": best_entry,
            "history": history,
        }

    def predict_proba(self, x: np.ndarray, device: str = "cpu") -> np.ndarray:
        if self.model is None:
            raise RuntimeError("TemporalSpatialMIModel is not initialized")
        tensor = torch.tensor(x.tolist(), dtype=torch.float32, device=device)
        self.model.to(device)
        self.model.eval()
        with torch.no_grad():
            logits = self.model(tensor)
            probabilities = F.softmax(logits, dim=1)
        return np.asarray(probabilities.detach().cpu().tolist(), dtype=np.float32)

    def summary(self) -> dict:
        return {
            "status": "trainable",
            "num_classes": self.config.num_classes,
            "temporal_kernel_sizes": self.config.temporal_kernel_sizes,
            "embedding_dim": self.config.embedding_dim,
            "loss": "CrossEntropyLoss(label_smoothing=0.05)",
            "optimizer": "AdamW",
            "learning_rate": self.config.learning_rate,
            "weight_decay": self.config.weight_decay,
            "batch_size": self.config.batch_size,
            "epochs": self.config.epochs,
            "patience": self.config.patience,
        }
