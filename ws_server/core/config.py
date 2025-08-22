"""Runtime configuration helpers."""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def get_tts_engine_default() -> str:
    """Return desired default TTS engine with fallback if Zonos is missing."""
    engine = os.getenv("TTS_ENGINE", "zonos").lower()
    if engine == "zonos":
        try:  # optional dependency
            from backend.tts.engine_zonos import ZonosTTSEngine  # type: ignore # noqa:F401
        except Exception as exc:  # pragma: no cover - import probe
            logger.warning("Zonos nicht verfügbar (%s) – falle auf Piper zurück", exc)
            engine = "piper"
    return engine
