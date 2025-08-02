import logging
from typing import Optional

try:
    import joblib  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    joblib = None

logger = logging.getLogger(__name__)

class IntentClassifier:
    """Optional einfacher Intent-Klassifizierer."""

    def __init__(self, model_path: Optional[str] = None):
        self.model = None
        if model_path and joblib:
            try:
                self.model = joblib.load(model_path)
                logger.info("Intent-Model geladen: %s", model_path)
            except Exception as exc:
                logger.error("Konnte Intent-Model nicht laden: %s", exc)

    def classify(self, text: str) -> str:
        if self.model:
            try:
                return self.model.predict([text])[0]
            except Exception as exc:
                logger.error("Intent-Klassifikation fehlgeschlagen: %s", exc)

        lower = text.lower()
        if any(word in lower for word in ["zeit", "uhrzeit", "wie spät"]):
            return "time_query"
        if any(word in lower for word in ["hallo", "hi", "guten tag"]):
            return "greeting"
        if any(word in lower for word in ["danke", "vielen dank"]):
            return "gratitude"
        if any(word in lower for word in ["frage", "wissen", "hilfe", "wetter", "garage", "status"]):
            return "external_request"
        return "unknown"
