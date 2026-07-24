# Pipeline

## Objective

Keep the project centered on 3-class motor imagery decoding:

- `left`
- `right`
- `feet`

## Training Pipeline

### 1. Raw Input

- Source: multi-channel EEG
- Labels: cue-based or event-based motor imagery labels normalized to:
  - `left`
  - `right`
  - `feet`

### 2. Preprocessing

- Bandpass filter: `0.5-40 Hz`
- Notch filter: `50 Hz` or `60 Hz`
- CAR / rereference
- ICA-based artifact removal
- Trial extraction or window slicing for training and realtime inference
- Artifact rejection and quality control

### 3. Shared Data Interface

- Unified output format: `(N, C, T)`
- Shared split policy for baseline and neural model
- Quality metadata:
  - valid-trial count
  - rejected-trial ratio
  - alignment error
  - per-class sample count

### 4. Baseline Branch

- `CSP / FBCSP`
- `LDA` as the first reference classifier
- Optional `SVM` after the basic pipeline is stable

### 5. Main Model Branch

- Contrastive learning is preserved as the representation-learning stage
- Planned model direction:
  - temporal-spatial lightweight encoder
  - optional channel attention
  - 3-class classifier head

### 6. Evaluation

- overall accuracy
- macro F1
- confusion matrix
- per-class precision / recall
- balanced accuracy

## Realtime Pipeline

```text
stream EEG
  -> buffer
  -> preprocessing
  -> window extraction
  -> MI decoder
  -> left/right/feet probabilities
  -> websocket messages
  -> monitor page
  -> interactive animation / control feedback
```

## Module Boundaries

- `models/preprocessing/`: filtering, artifact removal, windowing
- `models/datasets/`: label normalization, session loading, alignment
- `models/baselines/`: CSP/FBCSP and classical classifiers
- `models/contrastive/`: contrastive trainer and pretraining utilities
- `models/deep/`: neural MI encoders and classifier heads
- `models/tasks/`: task-facing classifier wrappers
- `models/realtime/`: buffer, inference runner, device-control trigger
- `backend/`: runtime service and websocket schema
- `frontend/`: page structure only
