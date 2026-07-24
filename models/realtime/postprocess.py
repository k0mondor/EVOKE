from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ProbabilitySmoother:
    alpha: float = 0.35
    _state: dict[str, float] = field(default_factory=dict)

    def smooth(self, probabilities: dict[str, float]) -> dict[str, float]:
        if not self._state:
            self._state = dict(probabilities)
            return dict(probabilities)

        next_state: dict[str, float] = {}
        for label, value in probabilities.items():
            previous = self._state.get(label, value)
            next_state[label] = (1.0 - self.alpha) * previous + self.alpha * value

        total = sum(next_state.values())
        if total > 1e-12:
            next_state = {label: value / total for label, value in next_state.items()}

        self._state = next_state
        return dict(next_state)
