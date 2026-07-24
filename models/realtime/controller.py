from dataclasses import dataclass


@dataclass(slots=True)
class DeviceControlDecision:
    action: str
    accepted: bool


def decide_device_action(mi_label: str, confidence: float) -> DeviceControlDecision:
    if confidence < 0.5:
        return DeviceControlDecision(action="hold", accepted=False)

    return DeviceControlDecision(action=f"emit_{mi_label}", accepted=True)
