# EEG Motor Imagery System

## Goal

This repository targets an online EEG motor imagery system for 3-class classification:

- left hand
- right hand
- feet

The project is designed around two training lines that share the same preprocessing pipeline:

- baseline line: FBCSP / CSP + LDA
- main model line: contrastive pretraining + lightweight temporal-spatial neural encoder

The final system should support:

- offline preprocessing and training
- subject/session quality checking
- online inference
- realtime web monitoring
- later integration with interactive control modules

## Task Definition

The final label space is:

- `left`: left-hand motor imagery
- `right`: right-hand motor imagery
- `feet`: feet motor imagery

The repository should keep raw experiment labels and model labels separated:

- raw labels come from experiment markers or annotation files
- model labels are normalized to `left / right / feet`

This separation makes later protocol changes easier and avoids coupling the model to a specific event naming scheme.

## Repository Layout

```text
backend/         FastAPI service skeleton and websocket schema
frontend/        Story page + monitor page structure
models/          Shared datasets, preprocessing, baselines, deep models, realtime logic
scripts/         Training entry points for baseline and main model
reports/         Evaluation outputs for future 3-class experiments
data/            Raw, interim, processed data folders
docs/            Supporting technical notes
```

## End-to-End Pipeline

```text
raw EEG + label file
  -> time alignment
  -> bandpass / notch / CAR
  -> ICA artifact removal
  -> trial extraction / windowing
  -> artifact rejection
  -> feature branch A: FBCSP / CSP
  -> feature branch B: temporal-spatial encoder
  -> 3-class classification
  -> evaluation reports
  -> realtime inference payloads
  -> web monitor UI
```

## Baseline Plan

The baseline line is used as a reliable reference and should be implemented before trusting any deep model gain.

Recommended baseline order:

1. `CAR + CSP + LDA`
2. `CAR + FBCSP + LDA`
3. optional: `CAR + FBCSP + SVM`

Why this baseline matters:

- MI tasks are strongly dependent on spatial patterns
- CSP/FBCSP is still a strong classical baseline for small EEG datasets
- a deep model must beat or at least match this baseline to justify added complexity

Expected baseline input:

- trial-based EEG or fixed windows from labeled MI segments
- unified sampling rate
- selected motor-related channels if channel selection is later introduced

Expected baseline output:

- 3-class probability
- predicted class
- confusion matrix
- per-class recall

## Main Model Structure

The main model line should remain lightweight enough for online use, but stronger than the current frequency-only baseline.

Recommended model design:

1. filter-bank input or multi-band preprocessing
2. temporal block for rhythm learning
3. spatial block for channel interaction
4. optional channel attention
5. embedding layer
6. 3-class classifier head

Recommended architecture idea:

- input: `(batch, channels, time)`
- temporal block:
  - multiple temporal kernels such as `15 / 31 / 63`
  - captures mu / beta patterns at different scales
- spatial block:
  - depthwise or grouped convolution across channels
  - learns lateralized motor imagery patterns
- attention block:
  - optional squeeze-excitation or channel attention
- head:
  - projection head for contrastive pretraining
  - classifier head for supervised fine-tuning

This model should be easier to deploy online than a heavy transformer while still being stronger than a small MLP on handcrafted features.

## Input Feature Design

Two parallel feature strategies are recommended.

### Baseline Features

- filter-bank EEG trials
- CSP or FBCSP projected features
- log-variance features

Suggested frequency bands for FBCSP:

- `8-12 Hz`
- `12-16 Hz`
- `16-22 Hz`
- `22-30 Hz`

These bands focus on the most relevant mu/beta ranges for motor imagery.

### Main Model Inputs

The main model should primarily use minimally processed time-series input:

- bandpass filtered EEG
- notch filtered EEG
- CAR-referenced EEG
- ICA-cleaned EEG
- fixed-length trial or window tensors

Optional additional inputs:

- Welch PSD branch
- bandpower summary branch
- STFT/time-frequency map branch

The preferred development order is:

1. raw time-series branch
2. optional multi-band branch
3. optional time-frequency branch

Do not overcomplicate the model before a strong CSP/FBCSP baseline is available.

## Training Strategy

### Shared Rules

Both baseline and main model must use:

- the same aligned EEG sessions
- the same class mapping
- the same train/validation/test split policy
- the same artifact rejection rules

This is necessary for fair comparison.

### Preprocessing Strategy

Current recommended preprocessing:

- bandpass: `0.5-40 Hz`
- notch: `50 Hz`
- rereference: `CAR`
- ICA: enabled for offline cleaning
- artifact rejection:
  - peak-to-peak threshold
  - RMS threshold
  - optional manual inspection for noisy sessions

For MI-specific experiments, an additional filter-bank branch centered around `8-30 Hz` should be introduced for baseline training.

### Data Split Strategy

Use strict split rules to avoid leakage:

- split by trial or by larger temporal blocks
- never randomly shuffle overlapping windows across train and validation
- keep a temporal gap between train and validation windows if sliding windows are used
- prefer session-wise or subject-wise evaluation when enough data becomes available

### Main Model Training Phases

Phase 1: contrastive pretraining

- run only on the training split
- apply EEG-friendly augmentations:
  - amplitude scaling
  - small Gaussian noise
  - mild time masking
  - light channel dropout

Phase 2: supervised fine-tuning

- fine-tune the encoder and train a 3-class head
- use early stopping
- save best validation checkpoint

Phase 3: optional subject calibration

- reuse a shared encoder
- fine-tune only the classifier head or a small adaptation layer for each subject

### Training Priority

Recommended order:

1. implement CSP/FBCSP baseline
2. stabilize shared preprocessing
3. build lightweight temporal-spatial neural model
4. add contrastive pretraining
5. evaluate cross-subject transfer

## Evaluation Metrics

Because the final task is 3-class MI, evaluation must go beyond plain accuracy.

Required metrics:

- overall accuracy
- macro F1
- per-class precision
- per-class recall
- confusion matrix
- balanced accuracy

Session/data quality metrics should also be tracked:

- alignment error in seconds
- number of valid trials/windows
- artifact rejection ratio
- kept-trial ratio per class
- sampling-rate normalization status

Recommended evaluation protocol:

- single-subject evaluation
- leave-one-session-out if multiple sessions exist
- later: leave-one-subject-out cross-subject evaluation

Important note:

- current `B1 / T / B2` binary results cannot be reused as final 3-class performance
- they can still be reused as pipeline sanity checks and data quality indicators

## Realtime Web Output Design

The online system should not expose only a hard class label. It should expose structured inference results for the frontend.

Recommended realtime output payload:

```json
{
  "timestamp_ms": 1784771007000,
  "mode": "motor_imagery_3class",
  "prediction": {
    "label": "left",
    "probabilities": {
      "left": 0.72,
      "right": 0.18,
      "feet": 0.10
    },
    "confidence": 0.72
  },
  "window": {
    "duration_ms": 4000,
    "stride_ms": 500
  },
  "signal_quality": {
    "artifact_score": 0.11,
    "usable": true
  }
}
```

Frontend monitor page should display at least:

- realtime EEG waveforms
- 3-class probability bars
- current predicted class
- signal quality / confidence
- optional topomap
- optional 3D brain visualization

Recommended visualization logic:

- use smoothed probabilities over recent windows
- highlight the highest class
- suppress hard switching when confidence is too low
- expose a `no_decision` or `low_confidence` state if needed

## Development Roadmap

1. finalize 3-class experiment label format
2. implement baseline branch: `FBCSP + LDA`
3. refactor current model branch toward temporal-spatial MI encoder
4. add strict 3-class evaluation reports
5. define realtime 3-class websocket payload
6. connect monitor page to model output

## Current Notes

- The current repository already supports time alignment, frequency-domain analysis, artifact handling, and single-subject experiments.
- The existing binary `idle vs intent` reports are transitional only.
- Final conclusions about `left / right / feet` performance must wait for real labeled 3-class data.
