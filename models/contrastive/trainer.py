from dataclasses import dataclass

import torch
from torch import nn
from torch.nn import functional as F


@dataclass(slots=True)
class ContrastiveTrainingConfig:
    batch_size: int = 32
    temperature: float = 0.1
    epochs: int = 30
    learning_rate: float = 1e-3
    weight_decay: float = 1e-4
    noise_std: float = 0.02
    feature_drop_prob: float = 0.1


def _augment(features: torch.Tensor, config: ContrastiveTrainingConfig) -> torch.Tensor:
    noise = torch.randn_like(features) * config.noise_std
    dropped = features.clone()
    mask = torch.rand_like(dropped) > config.feature_drop_prob
    return (dropped * mask) + noise


def _nt_xent_loss(z1: torch.Tensor, z2: torch.Tensor, temperature: float) -> torch.Tensor:
    z1 = F.normalize(z1, dim=1)
    z2 = F.normalize(z2, dim=1)
    embeddings = torch.cat([z1, z2], dim=0)
    similarity = embeddings @ embeddings.T / temperature

    batch_size = z1.shape[0]
    labels = torch.arange(batch_size, device=z1.device)
    labels = torch.cat([labels + batch_size, labels], dim=0)

    logits_mask = ~torch.eye(2 * batch_size, device=z1.device, dtype=torch.bool)
    masked_similarity = similarity.masked_select(logits_mask).reshape(2 * batch_size, -1)

    positive_similarity = torch.cat(
        [
            similarity[torch.arange(batch_size), torch.arange(batch_size) + batch_size],
            similarity[torch.arange(batch_size) + batch_size, torch.arange(batch_size)],
        ],
        dim=0,
    ).unsqueeze(1)
    logits = torch.cat([positive_similarity, masked_similarity], dim=1)
    targets = torch.zeros(logits.shape[0], device=z1.device, dtype=torch.long)
    return F.cross_entropy(logits, targets)


class ContrastiveTrainer:
    def __init__(self, config: ContrastiveTrainingConfig | None = None) -> None:
        self.config = config or ContrastiveTrainingConfig()

    def fit(self, encoder: nn.Module, features: torch.Tensor, device: str = "cpu"):
        if features.ndim != 3:
            raise ValueError(f"Expected [batch, channels, bands], got {tuple(features.shape)}")

        encoder.to(device)
        encoder.train()
        optimizer = torch.optim.AdamW(
            encoder.parameters(),
            lr=self.config.learning_rate,
            weight_decay=self.config.weight_decay,
        )

        history: list[float] = []
        features = features.to(device)
        for _ in range(self.config.epochs):
            permutation = torch.randperm(features.shape[0], device=device)
            losses: list[float] = []
            for start in range(0, features.shape[0], self.config.batch_size):
                indices = permutation[start : start + self.config.batch_size]
                batch = features[indices]
                if batch.shape[0] < 2:
                    continue

                view_a = _augment(batch, self.config)
                view_b = _augment(batch, self.config)
                z_a = encoder(view_a)
                z_b = encoder(view_b)
                loss = _nt_xent_loss(z_a, z_b, self.config.temperature)

                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                losses.append(float(loss.item()))

            history.append(sum(losses) / max(len(losses), 1))

        return {"status": "ok", "epochs": self.config.epochs, "loss_history": history}
