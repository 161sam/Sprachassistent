# DEPRECATION SHIM: nutzt die neue einheitliche Implementierung
from ws_server.tts.manager import TTSManager, TTSEngineType, TTSConfig
from ws_server.tts.voice_aliases import VOICE_ALIASES
__all__ = ["TTSManager","TTSEngineType","TTSConfig","VOICE_ALIASES"]
