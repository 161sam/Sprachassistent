import logging
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

try:
    import joblib  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    joblib = None

from .skills import load_all_skills

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
                    "schalte das licht ein",
                ]
                train_labels = [
                    "time_query",
                    "greeting",
                    "gratitude",
                    "knowledge",
                    "automation",
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
            for word in ["schalte", "workflow", "automation", "n8n", "trigger"]
        ):
            return IntentPrediction("automation", 0.5)
        if any(
            word in lower
            for word in ["frage", "wissen", "hilfe", "wetter", "garage", "status"]
        ):
            return IntentPrediction("knowledge", 0.5)
        return IntentPrediction("unknown", 0.0)


class IntentRouter:
    """Router, der Intents zu Skills oder externen Diensten leitet."""

    def __init__(self, skills_path: Optional[str | Path] = None) -> None:
        self.classifier = IntentClassifier()
        self.skills = load_all_skills(skills_path)
        self.flowise_url = os.getenv("FLOWISE_URL")
        self.n8n_host = os.getenv("N8N_HOST")
        self.n8n_port = os.getenv("N8N_PORT", "5678")

    async def route(self, text: str) -> str:
        prediction = self.classifier.classify(text)
        # Zuerst lokale Skills prüfen
        for skill in self.skills:
            if skill.intent_name == prediction.intent or skill.can_handle(text):
                return skill.handle(text)

        if prediction.intent == "automation" and self.n8n_host:
            return await self._call_n8n(text)

        if self.flowise_url and prediction.intent in {"knowledge", "unknown"}:
            return await self._call_flowise(text)

        return "Keine passende Antwort gefunden."

    async def _call_flowise(self, text: str) -> str:
        import aiohttp
        assert self.flowise_url is not None
        url = f"{self.flowise_url.rstrip('/')}/chat"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json={"question": text}) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("text") or data.get("answer") or ""
                    return f"[Flowise Fehler {resp.status}]"
        except Exception:  # pragma: no cover - network errors
            logger.error("Flowise request failed", exc_info=True)
            return "Flowise Fehler"

    async def _call_n8n(self, text: str) -> str:
        import aiohttp

        url = f"http://{self.n8n_host}:{self.n8n_port}/webhook/intent"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json={"query": text}) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("text") or data.get("answer") or ""
                    return f"[n8n Fehler {resp.status}]"
        except Exception:  # pragma: no cover - network errors
            logger.error("n8n request failed", exc_info=True)
            return "n8n Fehler"

