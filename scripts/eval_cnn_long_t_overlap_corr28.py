from __future__ import annotations

import copy
import itertools
import json
import random
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import accuracy_score, balanced_accuracy_score, confusion_matrix, precision_recall_fscore_support
from torch import nn
from torch.nn import functional as F

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from models.datasets.label_mapping import MI_CLASSES, MI_CLASS_TO_INDEX
from models.datasets.session_loader import load_eeg_csv, parse_filename_metadata
from models.deep.mi_tspnet import TemporalSpatialClassifier, TemporalSpatialEncoder, TemporalSpatialModelConfig
from models.preprocessing.filters import FilterConfig, apply_bandpass, apply_notch, apply_rereference
from models.preprocessing.windowing import WindowConfig, build_windows


OUTPUT_PATH = REPO_ROOT / "reports" / "ablations" / "cnn_long_t_overlap_corr28.json"
LONG_T_WAVEFORM_DIR = REPO_ROOT / "data" / "raw" / "long_t"
SAMPLING_RATE = 250
LONG_T_GROUP_IDS = (31, 32, 33, 34, 35)
FIXED_TASK_WINDOWS = (
    ("T1", "left", 10.0, 20.0),
    ("T2", "right", 30.0, 40.0),
    ("T3", "feet", 50.0, 60.0),
)


@dataclass(slots=True)
class WindowSample:
    group_index: int
    eeg_file: str
    mi_label: str
    label_index: int
    task_key: str
    window_rank: int
    start_sample: int
    end_sample: int
    data: np.ndarray
    ptp: float
    rms: float


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def fit_artifact_thresholds(samples: list[WindowSample]) -> dict[str, float]:
    ptp = np.asarray([sample.ptp for sample in samples], dtype=np.float64)
    rms = np.asarray([sample.rms for sample in samples], dtype=np.float64)

    def robust_threshold(values: np.ndarray) -> float:
        median = float(np.median(values))
        mad = float(np.median(np.abs(values - median)))
        if mad <= 1e-12:
            return float(values.max())
        return median + 3.0 * mad

    return {
        "ptp_threshold": robust_threshold(ptp),
        "rms_threshold": robust_threshold(rms),
    }


def filter_artifacts(samples: list[WindowSample], thresholds: dict[str, float]) -> tuple[list[WindowSample], dict[str, int | float]]:
    kept = [
        sample
        for sample in samples
        if sample.ptp <= thresholds["ptp_threshold"] and sample.rms <= thresholds["rms_threshold"]
    ]
    rejected = len(samples) - len(kept)
    return kept, {
        "total_windows": len(samples),
        "kept_windows": len(kept),
        "rejected_windows": rejected,
        "rejected_ratio": 0.0 if len(samples) == 0 else rejected / float(len(samples)),
    }


def build_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=np.arange(len(MI_CLASSES)),
        zero_division=0,
    )
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "macro_f1": float(np.mean(f1)),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=np.arange(len(MI_CLASSES))).tolist(),
        "per_class": {
            label: {
                "precision": float(precision[index]),
                "recall": float(recall[index]),
                "f1": float(f1[index]),
                "support": int(support[index]),
            }
            for index, label in enumerate(MI_CLASSES)
        },
    }


def summarize_by_class(samples: list[WindowSample]) -> dict[str, int]:
    counts = {label: 0 for label in MI_CLASSES}
    for sample in samples:
        counts[sample.mi_label] += 1
    return counts


def build_sample_arrays(samples: list[WindowSample]) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray([sample.data for sample in samples], dtype=np.float32)
    y = np.asarray([sample.label_index for sample in samples], dtype=np.int64)
    return x, y


def select_latest_five_waveforms() -> list[Path]:
    eeg_files = sorted(
        LONG_T_WAVEFORM_DIR.glob("ads1299_*.csv"),
        key=lambda path: parse_filename_metadata(path)[0],
    )
    if len(eeg_files) < 5:
        raise RuntimeError("Need at least five ads1299 waveform files for long-T evaluation")
    return eeg_files[-5:]


def build_task_windows(signal: np.ndarray, start_s: float, end_s: float) -> list[tuple[np.ndarray, int, int]]:
    start_sample = int(round(start_s * SAMPLING_RATE))
    end_sample = min(signal.shape[0], int(round(end_s * SAMPLING_RATE)))
    if end_sample <= start_sample:
        return []

    segment_signal = signal[start_sample:end_sample]
    records = build_windows(
        segment_signal,
        WindowConfig(window_size_s=4.0, stride_s=2.0, sampling_rate=SAMPLING_RATE),
    )
    return [
        (np.asarray(record.data.T, dtype=np.float32), start_sample + record.start_sample, start_sample + record.end_sample)
        for record in records
    ]


def build_dynamic_corr_channels(window: np.ndarray) -> np.ndarray:
    # Normalize each channel within the window, then form pairwise products.
    centered = window - window.mean(axis=1, keepdims=True)
    scale = window.std(axis=1, keepdims=True)
    scale = np.where(scale < 1e-6, 1.0, scale)
    normalized = centered / scale

    derived_channels: list[np.ndarray] = []
    for i, j in itertools.combinations(range(normalized.shape[0]), 2):
        derived_channels.append(normalized[i] * normalized[j])
    return np.asarray(derived_channels, dtype=np.float32)


def load_group_samples() -> tuple[list[WindowSample], dict[int, dict[str, object]]]:
    samples: list[WindowSample] = []
    group_summaries: dict[int, dict[str, object]] = {}

    filter_config = FilterConfig(
        low_cut_hz=4.0,
        high_cut_hz=30.0,
        notch_hz=50.0,
        sampling_rate=SAMPLING_RATE,
        rereference_mode="none",
    )

    pair_names = [f"CH{i+1}-CH{j+1}" for i, j in itertools.combinations(range(8), 2)]

    for group_index, eeg_path in zip(LONG_T_GROUP_IDS, select_latest_five_waveforms()):
        signal, channel_names = load_eeg_csv(eeg_path)
        signal = apply_rereference(signal, filter_config)
        signal = apply_bandpass(signal, filter_config)
        signal = apply_notch(signal, filter_config)

        group_summaries[group_index] = {
            "eeg_file": eeg_path.name,
            "source_channel_names": channel_names,
            "derived_channel_names": pair_names,
            "num_samples": int(signal.shape[0]),
            "duration_s": float(signal.shape[0] / SAMPLING_RATE),
            "task_windows_before_artifact": {},
        }

        for task_key, mi_label, start_s, end_s in FIXED_TASK_WINDOWS:
            windows = build_task_windows(signal, start_s, end_s)
            group_summaries[group_index]["task_windows_before_artifact"][task_key] = len(windows)
            for rank, (raw_window, start_sample, end_sample) in enumerate(windows):
                corr_window = build_dynamic_corr_channels(raw_window)
                samples.append(
                    WindowSample(
                        group_index=group_index,
                        eeg_file=eeg_path.name,
                        mi_label=mi_label,
                        label_index=MI_CLASS_TO_INDEX[mi_label],
                        task_key=task_key,
                        window_rank=rank,
                        start_sample=int(start_sample),
                        end_sample=int(end_sample),
                        data=corr_window,
                        ptp=float(np.ptp(raw_window, axis=1).max()),
                        rms=float(np.sqrt(np.mean(raw_window**2))),
                    )
                )

    return samples, group_summaries


def train_temporal_model(
    train_x: np.ndarray,
    train_y: np.ndarray,
    val_x: np.ndarray,
    val_y: np.ndarray,
    seed: int,
) -> tuple[dict, np.ndarray]:
    set_seed(seed)
    config = TemporalSpatialModelConfig(
        num_classes=len(MI_CLASSES),
        dropout=0.25,
        embedding_dim=64,
        temporal_kernel_sizes=(15, 31, 63),
        temporal_filters=16,
        spatial_filters=32,
        learning_rate=1e-3,
        weight_decay=1e-4,
        batch_size=8,
        epochs=120,
        patience=25,
        label_smoothing=0.05,
    )
    device = "cpu"

    encoder = TemporalSpatialEncoder(num_channels=train_x.shape[1], config=config)
    model = TemporalSpatialClassifier(encoder=encoder, config=config).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay)
    criterion = nn.CrossEntropyLoss(label_smoothing=config.label_smoothing)

    train_features = torch.tensor(train_x.tolist(), dtype=torch.float32, device=device)
    train_targets = torch.tensor(train_y.tolist(), dtype=torch.long, device=device)
    val_features = torch.tensor(val_x.tolist(), dtype=torch.float32, device=device)
    val_targets = torch.tensor(val_y.tolist(), dtype=torch.long, device=device)

    best_state: dict | None = None
    best_entry: dict[str, float] | None = None
    best_val_loss = float("inf")
    patience_counter = 0

    for epoch_index in range(config.epochs):
        model.train()
        permutation = torch.randperm(train_features.shape[0], device=device)
        batch_losses: list[float] = []
        batch_accs: list[float] = []

        for start in range(0, train_features.shape[0], config.batch_size):
            indices = permutation[start : start + config.batch_size]
            batch_x = train_features[indices]
            batch_y = train_targets[indices]

            logits = model(batch_x)
            loss = criterion(logits, batch_y)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            batch_losses.append(float(loss.item()))
            batch_accs.append(float((logits.argmax(dim=1) == batch_y).float().mean().item()))

        model.eval()
        with torch.no_grad():
            val_logits = model(val_features)
            val_loss = float(criterion(val_logits, val_targets).item())
            val_acc = float((val_logits.argmax(dim=1) == val_targets).float().mean().item())

        entry = {
            "epoch": float(epoch_index + 1),
            "train_loss": float(np.mean(batch_losses) if batch_losses else 0.0),
            "train_acc": float(np.mean(batch_accs) if batch_accs else 0.0),
            "val_loss": val_loss,
            "val_acc": val_acc,
        }
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_entry = entry
            best_state = copy.deepcopy(model.state_dict())
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= config.patience:
                break

    if best_state is None or best_entry is None:
        raise RuntimeError("Training did not produce a best validation checkpoint")

    model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        probabilities = np.asarray(F.softmax(model(val_features), dim=1).detach().cpu().tolist(), dtype=np.float32)
    return best_entry, probabilities


def main() -> None:
    set_seed(42)
    all_samples, group_summaries = load_group_samples()

    fold_reports: list[dict] = []
    excluded_folds: list[dict] = []
    aggregate_predictions = {"cnn_corr28": {"y_true": [], "y_pred": []}}

    for held_out_group in LONG_T_GROUP_IDS:
        train_candidates = [sample for sample in all_samples if sample.group_index != held_out_group]
        val_candidates = [sample for sample in all_samples if sample.group_index == held_out_group]
        thresholds = fit_artifact_thresholds(train_candidates)
        train_samples, train_artifact = filter_artifacts(train_candidates, thresholds)
        val_samples, val_artifact = filter_artifacts(val_candidates, thresholds)

        train_labels = {sample.mi_label for sample in train_samples}
        if set(MI_CLASSES) - train_labels:
            raise RuntimeError(f"Train split for G{held_out_group} is missing classes")

        val_labels = {sample.mi_label for sample in val_samples}
        missing_val_classes = sorted(set(MI_CLASSES) - val_labels)
        if missing_val_classes:
            excluded_folds.append(
                {
                    "held_out_group": held_out_group,
                    "reason": "validation_missing_classes_after_artifact_rejection",
                    "missing_classes": missing_val_classes,
                    "thresholds": thresholds,
                    "train_artifact": train_artifact,
                    "val_artifact": val_artifact,
                    "train_counts": summarize_by_class(train_samples),
                    "val_counts_before_exclusion": summarize_by_class(val_candidates),
                    "val_counts_after_artifact": summarize_by_class(val_samples),
                }
            )
            continue

        train_x, train_y = build_sample_arrays(train_samples)
        val_x, val_y = build_sample_arrays(val_samples)
        cnn_training, cnn_proba = train_temporal_model(train_x, train_y, val_x, val_y, seed=2100 + held_out_group)
        cnn_pred = np.argmax(cnn_proba, axis=1)

        aggregate_predictions["cnn_corr28"]["y_true"].extend(val_y.tolist())
        aggregate_predictions["cnn_corr28"]["y_pred"].extend(cnn_pred.tolist())

        fold_reports.append(
            {
                "held_out_group": held_out_group,
                "thresholds": thresholds,
                "train_artifact": train_artifact,
                "val_artifact": val_artifact,
                "train_counts": summarize_by_class(train_samples),
                "val_counts": summarize_by_class(val_samples),
                "methods": {
                    "cnn_corr28": {
                        "training": {"best": cnn_training},
                        "metrics": build_metrics(val_y, cnn_pred),
                    }
                },
            }
        )

    y_true = np.asarray(aggregate_predictions["cnn_corr28"]["y_true"], dtype=np.int64)
    y_pred = np.asarray(aggregate_predictions["cnn_corr28"]["y_pred"], dtype=np.int64)
    fold_accs = [report["methods"]["cnn_corr28"]["metrics"]["accuracy"] for report in fold_reports]
    fold_bal_accs = [report["methods"]["cnn_corr28"]["metrics"]["balanced_accuracy"] for report in fold_reports]

    report = {
        "protocol": {
            "assumption": "latest five waveform files are the new long-T groups",
            "groups": list(LONG_T_GROUP_IDS),
            "waveforms": [path.name for path in select_latest_five_waveforms()],
            "evaluation": "leave-one-group-out",
            "sampling_rate_hz": SAMPLING_RATE,
            "window_size_s": 4.0,
            "stride_s": 2.0,
            "window_selection": "all_overlapping_4s_windows_per_10s_task",
            "fixed_task_windows_s": {
                "T1_left": [10.0, 20.0],
                "T2_right": [30.0, 40.0],
                "T3_feet": [50.0, 60.0],
            },
            "feature_transform": "28 dynamic correlation channels from pairwise products of per-window z-scored EEG channels",
            "artifact_rule": "train-fit / val-apply, reject windows with ptp or rms above median + 3*MAD, computed on original 8-channel EEG window",
            "preprocessing": {
                "bandpass_hz": [4.0, 30.0],
                "notch_hz": 50.0,
                "rereference": "none",
                "ica": False,
            },
            "excluded_folds": excluded_folds,
        },
        "group_summaries": group_summaries,
        "fold_reports": fold_reports,
        "summary": {
            "cnn_corr28": {
                "overall": build_metrics(y_true, y_pred),
                "fold_accuracy_mean": float(np.mean(fold_accs)) if fold_accs else 0.0,
                "fold_accuracy_std": float(np.std(fold_accs)) if fold_accs else 0.0,
                "fold_balanced_accuracy_mean": float(np.mean(fold_bal_accs)) if fold_bal_accs else 0.0,
                "fold_balanced_accuracy_std": float(np.std(fold_bal_accs)) if fold_bal_accs else 0.0,
            }
        },
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output_path": str(OUTPUT_PATH), "summary": report["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
