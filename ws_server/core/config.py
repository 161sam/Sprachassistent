"""Runtime configuration helpers."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Central default values. They mirror the previous contents of ``.env.defaults``
# so that configuration is maintained in a single place.
DEFAULT_ENV: dict[str, str] = {
    "WS_HOST": "127.0.0.1",
    "WS_PORT": "48231",
    "METRICS_PORT": "48232",
    "STT_ENGINE": "faster-whisper",
    "TTS_ENGINE": "zonos",
    "TTS_SPEED": "1.0",
    "TTS_VOLUME": "1.0",
    "TTS_MODEL_DIR": "./models",
    "ZONOS_MODEL": "Zyphra/Zonos-v0.1-transformer",
    "ZONOS_LANG": "de-de",
    "ZONOS_VOICE": "thorsten",
    "ZONOS_SPEAKER_DIR": "spk_cache",
    "TTS_OUTPUT_SR": "48000",
    "LLM_ENABLED": "true",
    "LLM_API_BASE": "http://127.0.0.1:1234/v1",
    "LLM_DEFAULT_MODEL": "auto",
    "LLM_TEMPERATURE": "0.7",
    "LLM_MAX_TOKENS": "256",
    "LLM_MAX_TURNS": "5",
    "LLM_TIMEOUT_SECONDS": "20",
    "LLM_SYSTEM_PROMPT": (
        "You are a friendly voice assistant. Reply in short, natural sentences that "
        "sound like speech. Avoid lists or Markdown formatting. If something is "
        "unclear, ask a brief follow-up question."
    ),
}


def load_env(path: Optional[str | Path] = None) -> None:
    """Load environment variables and apply defaults.

    Parameters
    ----------
    path:
        Optional path to a ``.env`` file. If ``None`` the repository root
        ``.env`` is used when present.
    """

    env_path = Path(path) if path else Path(".env")
    if env_path.exists():
        load_dotenv(env_path, override=False)

    for key, value in DEFAULT_ENV.items():
        os.environ.setdefault(key, value)


def get_tts_engine_default() -> str:
    """Return desired default TTS engine with fallback if Zonos is missing."""

    engine = os.getenv("TTS_ENGINE", "zonos").lower()
    if engine == "zonos":
        try:  # optional dependency
            from backend.tts.engine_zonos import ZonosTTSEngine  # type: ignore # noqa: F401
        except Exception as exc:  # pragma: no cover - import probe
            logger.warning("Zonos nicht verfügbar (%s) – falle auf Piper zurück", exc)
            engine = "piper"
    return engine
