"""Text-to-Speech utilities and engine exports."""

from .voice_aliases import VOICE_ALIASES, EngineVoice
from .voice_validation import validate_voice_assets

try:  # pragma: no cover - optional dependencies may be missing
    from .manager import TTSManager, TTSConfig, TTSEngineType
    __all__ = [
        "TTSManager",
        "TTSConfig",
        "TTSEngineType",
        "VOICE_ALIASES",
        "EngineVoice",
        "validate_voice_assets",
    ]
except Exception:  # pragma: no cover - expose minimal API if manager unavailable
    __all__ = ["VOICE_ALIASES", "EngineVoice", "validate_voice_assets"]
