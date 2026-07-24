MI_CLASSES = ("left", "right", "feet")

MI_CLASS_TO_INDEX = {label: index for index, label in enumerate(MI_CLASSES)}
MI_INDEX_TO_CLASS = {index: label for label, index in MI_CLASS_TO_INDEX.items()}


def normalize_mi_label(label: str) -> str:
    normalized = label.strip().lower()
    aliases = {
        "left_hand": "left",
        "left": "left",
        "right_hand": "right",
        "right": "right",
        "foot": "feet",
        "feet": "feet",
        "idle": "feet",
    }
    if normalized not in aliases:
        raise KeyError(f"Unsupported MI label: {label}")
    return aliases[normalized]
