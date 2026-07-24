from dataclasses import dataclass

from models.realtime.signals import signal_code_for_label


@dataclass(slots=True)
class DeviceControlDecision:
    action: str
    accepted: bool
    reason: str
    signal_code: int | None = None


@dataclass(slots=True)
class DeviceActionController:
    min_confidence: float = 0.55
    cooldown_ms: int = 1200
    _last_accepted_at_ms: int = 0

    def decide(
        self,
        *,
        mi_label: str,
        confidence: float,
        usable: bool,
        timestamp_ms: int,
    ) -> DeviceControlDecision:
        if not usable:
            return DeviceControlDecision(action="hold", accepted=False, reason="low_quality", signal_code=None)
        if confidence < self.min_confidence:
            return DeviceControlDecision(action="hold", accepted=False, reason="low_confidence", signal_code=None)
        if self._last_accepted_at_ms and (timestamp_ms - self._last_accepted_at_ms) < self.cooldown_ms:
            return DeviceControlDecision(action="hold", accepted=False, reason="cooldown", signal_code=None)

        self._last_accepted_at_ms = timestamp_ms
        return DeviceControlDecision(
            action=f"emit_{mi_label}",
            accepted=True,
            reason="accepted",
            signal_code=signal_code_for_label(mi_label),
        )
