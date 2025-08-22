import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

try:
    import joblib  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    joblib = None

logger = logging.getLogger(__name__)


@dataclass
class IntentPrediction:
    intent: str
    confidence: float


class IntentClassifier:
    """Intent-Klassifizierer mit optionalem ML-Modell."""

    def __init__(self, model_path: Optional[str] = "models/intent_classifier.bin"):
        self.model = None
        if joblib and model_path and Path(model_path).exists():
            try:
                self.model = joblib.load(model_path)
                logger.info("Intent-Model geladen: %s", model_path)
            except Exception as exc:
                logger.error("Konnte Intent-Model nicht laden: %s", exc)
        else:
            # Train a lightweight model if no pre-trained model is available
            try:
                from sklearn.pipeline import Pipeline
                from sklearn.feature_extraction.text import TfidfVectorizer
                from sklearn.linear_model import LogisticRegression

                train_texts = [
                    "wie spät ist es",
                    "hallo da",
                    "danke dir",
                    "frage zum wetter",
                ]
                train_labels = [
                    "time_query",
                    "greeting",
                    "gratitude",
                    "external_request",
                ]
                self.model = Pipeline([
                    ("vec", TfidfVectorizer()),
                    ("clf", LogisticRegression(max_iter=200)),
                ])
                self.model.fit(train_texts, train_labels)
                logger.info("Intent-Model im Speicher trainiert")
            except Exception as exc:
                logger.warning(
                    "Kein Intent-Model geladen, verwende Schlüsselwort-Fallback (%s)",
                    exc,
                )
                self.model = None

    def classify(self, text: str) -> IntentPrediction:
        if self.model:
            try:
                probs = self.model.predict_proba([text])[0]
                idx = probs.argmax()
                intent = self.model.classes_[idx]
                confidence = float(probs[idx])
                logger.debug("Intent %s mit %.2f%%", intent, confidence * 100)
                return IntentPrediction(intent, confidence)
            except Exception as exc:
                logger.error("Intent-Klassifikation fehlgeschlagen: %s", exc)

        lower = text.lower()
        if any(word in lower for word in ["zeit", "uhrzeit", "wie spät"]):
            return IntentPrediction("time_query", 0.5)
        if any(word in lower for word in ["hallo", "hi", "guten tag"]):
            return IntentPrediction("greeting", 0.5)
        if any(word in lower for word in ["danke", "vielen dank"]):
            return IntentPrediction("gratitude", 0.5)
        if any(
            word in lower
            for word in ["frage", "wissen", "hilfe", "wetter", "garage", "status"]
        ):
            return IntentPrediction("external_request", 0.5)
        return IntentPrediction("unknown", 0.0)

