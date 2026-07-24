from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import re

import numpy as np
import pandas as pd

from models.datasets.label_mapping import normalize_mi_label


TIMESTAMP_PATTERN = re.compile(r"(?P<date>\d{8})_(?P<time>\d{6})_(?P<fs>\d+)sps", re.IGNORECASE)
ADS1299_PATTERN = re.compile(r"ads1299_(?P<date>\d{8})_(?P<time>\d{6})", re.IGNORECASE)


@dataclass(slots=True)
class AlignmentInfo:
    mode: str
    sampling_rate: int
    duration_s: float
    file_start_bjt: datetime
    file_end_bjt: datetime
    alignment_error_s: float


@dataclass(slots=True)
class SegmentInfo:
    segment_label: str
    start_time_bjt: datetime
    end_time_bjt: datetime
    start_sample: int
    end_sample: int
    mi_label: str


def parse_filename_metadata(csv_path: str | Path) -> tuple[datetime, int]:
    match = TIMESTAMP_PATTERN.search(Path(csv_path).name)
    if match is not None:
        timestamp = datetime.strptime(
            f"{match.group('date')}_{match.group('time')}",
            "%Y%m%d_%H%M%S",
        )
        sampling_rate = int(match.group("fs"))
        return timestamp, sampling_rate

    ads_match = ADS1299_PATTERN.search(Path(csv_path).name)
    if ads_match is not None:
        timestamp = datetime.strptime(
            f"{ads_match.group('date')}_{ads_match.group('time')}",
            "%Y%m%d_%H%M%S",
        )
        return timestamp, 500

    raise ValueError(f"Cannot parse timestamp / sample rate from: {csv_path}")


def load_eeg_csv(csv_path: str | Path) -> tuple[np.ndarray, list[str]]:
    frame = pd.read_csv(csv_path)
    channel_names = list(frame.columns)
    signal = frame.to_numpy(dtype=np.float64)
    return signal, channel_names


def load_label_csv(csv_path: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(csv_path)
    frame["start_time_bjt"] = pd.to_datetime(frame["start_time_bjt"])
    frame["end_time_bjt"] = pd.to_datetime(frame["end_time_bjt"])
    return frame.sort_values("segment_index").reset_index(drop=True)


def _score_alignment(
    candidate_start: datetime,
    candidate_end: datetime,
    label_start: datetime,
    label_end: datetime,
) -> float:
    return abs((candidate_start - label_start).total_seconds()) + abs((candidate_end - label_end).total_seconds())


def infer_alignment(eeg_csv_path: str | Path, label_frame: pd.DataFrame, num_samples: int) -> AlignmentInfo:
    filename_time, sampling_rate = parse_filename_metadata(eeg_csv_path)
    duration_s = num_samples / float(sampling_rate)

    label_start = label_frame["start_time_bjt"].min().to_pydatetime()
    label_end = label_frame["end_time_bjt"].max().to_pydatetime()

    as_start = AlignmentInfo(
        mode="filename_as_start",
        sampling_rate=sampling_rate,
        duration_s=duration_s,
        file_start_bjt=filename_time,
        file_end_bjt=filename_time + timedelta(seconds=duration_s),
        alignment_error_s=_score_alignment(
            filename_time,
            filename_time + timedelta(seconds=duration_s),
            label_start,
            label_end,
        ),
    )
    as_end = AlignmentInfo(
        mode="filename_as_end",
        sampling_rate=sampling_rate,
        duration_s=duration_s,
        file_start_bjt=filename_time - timedelta(seconds=duration_s),
        file_end_bjt=filename_time,
        alignment_error_s=_score_alignment(
            filename_time - timedelta(seconds=duration_s),
            filename_time,
            label_start,
            label_end,
        ),
    )
    return as_start if as_start.alignment_error_s <= as_end.alignment_error_s else as_end


def infer_mi_label_from_row(
    segment_label: str,
    segment_description: str | None = None,
    segment_key: str | None = None,
    task_text: str | None = None,
    task_code: str | None = None,
) -> str:
    candidates = [segment_description or "", segment_key or "", segment_label, task_text or "", task_code or ""]
    for candidate in candidates:
        text = candidate.strip().lower()
        if not text:
            continue
        if text in {"t1", "left", "left_hand"}:
            return "left"
        if text in {"t2", "right", "right_hand"}:
            return "right"
        if text in {"t3", "feet", "foot", "idle"}:
            return "feet"
        if "left" in text or "zuo" in text or "左" in text:
            return "left"
        if "right" in text or "you" in text or "右" in text:
            return "right"
        if "feet" in text or "foot" in text or "jiao" in text or "脚" in text:
            return "feet"
    return normalize_mi_label(segment_label)


def build_segments(label_frame: pd.DataFrame, alignment: AlignmentInfo, num_samples: int) -> list[SegmentInfo]:
    segments: list[SegmentInfo] = []
    for row in label_frame.itertuples(index=False):
        start_delta_s = (row.start_time_bjt.to_pydatetime() - alignment.file_start_bjt).total_seconds()
        end_delta_s = (row.end_time_bjt.to_pydatetime() - alignment.file_start_bjt).total_seconds()

        start_sample = max(0, int(round(start_delta_s * alignment.sampling_rate)))
        end_sample = min(num_samples, int(round(end_delta_s * alignment.sampling_rate)))
        if end_sample <= start_sample:
            continue

        segments.append(
            SegmentInfo(
                segment_label=row.segment_label,
                start_time_bjt=row.start_time_bjt.to_pydatetime(),
                end_time_bjt=row.end_time_bjt.to_pydatetime(),
                start_sample=start_sample,
                end_sample=end_sample,
                mi_label=infer_mi_label_from_row(
                    row.segment_label,
                    getattr(row, "segment_description", None),
                    getattr(row, "segment_key", None),
                    getattr(row, "task_text", None),
                    getattr(row, "task_code", None),
                ),
            )
        )
    return segments
