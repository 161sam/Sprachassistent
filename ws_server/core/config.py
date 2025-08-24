"""Runtime configuration helpers."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:  # pragma: no cover - optional dependency
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    def load_dotenv(*_args, **_kwargs):
        return False

logger = logging.getLogger(__name__)

# Central default values. They mirror the previous contents of ``.env.defaults``
# so that configuration is maintained in a single place.
DEFAULT_ENV: dict[str, str] = {
    "WS_HOST": "127.0.0.1",
    "WS_PORT": "48231",
    "METRICS_PORT": "48232",
    "STT_MODEL": "tiny",
    "STT_DEVICE": "cpu",
    "TTS_ENGINE": "zonos",
    "TTS_VOICE": "de-thorsten-low",
    "JWT_SECRET": "devsecret",
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
        "You are a friendly voice assistant. Answer in short, punctuated sentences "
        "and keep responses under 500 characters. Avoid lists or Markdown formatting. "
        "If something is unclear, ask a brief follow-up question."
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

    engine = os.getenv("TTS_ENGINE", DEFAULT_ENV["TTS_ENGINE"]).lower()
    if engine == "zonos":
        try:  # optional dependency
            from backend.tts.engine_zonos import ZonosTTSEngine  # type: ignore # noqa: F401
        except Exception as exc:  # pragma: no cover - import probe
            logger.warning("Zonos nicht verfügbar (%s) – falle auf Piper zurück", exc)
            engine = "piper"
    return engine


def _as_bool(value: str) -> bool:
    return value.lower() in {"1", "true", "yes"}


@dataclass
class Config:
    """Central application configuration loaded from environment."""

    ws_host: str
    ws_port: int
    metrics_port: int
    stt_model: str
    stt_device: str
    tts_engine: str
    tts_voice: str
    jwt_secret: str
    jwt_bypass: bool
    jwt_allow_plain: bool
    llm_system_prompt: str

    @classmethod
    def from_env(cls) -> "Config":
        """Construct configuration using the current environment."""

        load_env()

        return cls(
            ws_host=os.getenv("WS_HOST", DEFAULT_ENV["WS_HOST"]),
            ws_port=int(os.getenv("WS_PORT", DEFAULT_ENV["WS_PORT"])),
            metrics_port=int(os.getenv("METRICS_PORT", DEFAULT_ENV["METRICS_PORT"])),
            stt_model=os.getenv("STT_MODEL", DEFAULT_ENV["STT_MODEL"]),
            stt_device=os.getenv("STT_DEVICE", DEFAULT_ENV["STT_DEVICE"]),
            tts_engine=get_tts_engine_default(),
            tts_voice=os.getenv("TTS_VOICE", DEFAULT_ENV["TTS_VOICE"]),
            jwt_secret=os.getenv("JWT_SECRET", DEFAULT_ENV["JWT_SECRET"]),
            jwt_bypass=_as_bool(os.getenv("JWT_BYPASS", "0")),
            jwt_allow_plain=_as_bool(os.getenv("JWT_ALLOW_PLAIN", "0")),
            llm_system_prompt=os.getenv(
                "LLM_SYSTEM_PROMPT", DEFAULT_ENV["LLM_SYSTEM_PROMPT"]
            ),
        )


# Load configuration once at import time for convenience
config = Config.from_env()


__all__ = ["Config", "config", "load_env", "get_tts_engine_default"]

LLM_BASE_URL = os.getenv('LLM_BASE_URL', '')

LLM_API_KEY = os.getenv('LLM_API_KEY', '')

FLOWISE_URL = os.getenv('FLOWISE_URL','')

FLOWISE_TOKEN = os.getenv('FLOWISE_TOKEN','')

N8N_URL = os.getenv('N8N_URL','')

N8N_TOKEN = os.getenv('N8N_TOKEN','')
