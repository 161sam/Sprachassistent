"""Re-export of the TTS manager for uniform imports."""

from backend.tts.tts_manager import TTSManager, TTSConfig, TTSEngineType
from .voice_utils import canonicalize_voice, expand_aliases

__all__ = ["TTSManager", "TTSConfig", "TTSEngineType"]
