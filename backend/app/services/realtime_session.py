from dataclasses import dataclass, field

from models.realtime.buffer import RollingEEGBuffer
from models.realtime.controller import decide_device_action
from models.realtime.inference import RealtimeInferenceRunner


@dataclass(slots=True)
class RealtimeSession:
    buffer: RollingEEGBuffer = field(default_factory=RollingEEGBuffer)
    runner: RealtimeInferenceRunner = field(default_factory=RealtimeInferenceRunner)

    def push_frame(self, frame: dict[str, list[float]]) -> dict | None:
        self.buffer.append(frame)
        window = self.buffer.build_window()
        if window is None:
            return None

        result = self.runner.predict(window)
        action = decide_device_action(result.label, result.confidence)
        return {
            "prediction": result,
            "device_action": action,
        }
