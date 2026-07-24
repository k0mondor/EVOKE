from dataclasses import dataclass, field

from models.tasks.mi_classifier import MIClassifier, MIPrediction


@dataclass(slots=True)
class RealtimeInferenceResult:
    label: str
    probabilities: dict[str, float]
    confidence: float


@dataclass(slots=True)
class RealtimeInferenceRunner:
    classifier: MIClassifier = field(default_factory=MIClassifier)

    def predict(self, window) -> RealtimeInferenceResult:
        prediction: MIPrediction = self.classifier.predict(window)
        confidence = max(prediction.probabilities.values())
        return RealtimeInferenceResult(
            label=prediction.label,
            probabilities=prediction.probabilities,
            confidence=confidence,
        )
