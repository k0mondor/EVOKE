from collections import deque
from dataclasses import dataclass, field


@dataclass(slots=True)
class RollingEEGBuffer:
    max_frames: int = 20
    frames: deque[dict[str, list[float]]] = field(default_factory=deque)

    def append(self, frame: dict[str, list[float]]) -> None:
        self.frames.append(frame)
        while len(self.frames) > self.max_frames:
            self.frames.popleft()

    def build_window(self) -> dict[str, list[float]] | None:
        if not self.frames:
            return None
        return self.frames[-1]
