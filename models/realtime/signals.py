from __future__ import annotations

MI_LABEL_TO_SIGNAL_CODE: dict[str, int] = {
    "left": 0,
    "right": 1,
    "feet": 2,
}

SIGNAL_CODE_TO_MI_LABEL: dict[int, str] = {
    code: label for label, code in MI_LABEL_TO_SIGNAL_CODE.items()
}


def signal_code_for_label(label: str) -> int:
    if label not in MI_LABEL_TO_SIGNAL_CODE:
        raise KeyError(f"Unsupported MI label: {label}")
    return MI_LABEL_TO_SIGNAL_CODE[label]
