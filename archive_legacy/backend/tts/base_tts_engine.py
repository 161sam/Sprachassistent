# DEPRECATION SHIM: zentrale Basisklassen leben unter ws_server/tts/base_tts_engine.py
try:
    from ws_server.tts.base_tts_engine import (
        BaseTTSEngine, TTSConfig, TTSResult, TTSInitializationError, TTSSynthesisError
    )
except Exception:
    # Minimal-Fallbacks, falls Namen im Zielmodul variieren
    from ws_server.tts.base_tts_engine import (
        BaseTTSEngine, TTSConfig, TTSResult
    )
    try:
        from ws_server.tts.base_tts_engine import TTSInitializationError
    except Exception:
        class TTSInitializationError(Exception): ...
    try:
        from ws_server.tts.base_tts_engine import TTSSynthesisError
    except Exception:
        class TTSSynthesisError(Exception): ...
__all__ = ["BaseTTSEngine","TTSConfig","TTSResult","TTSInitializationError","TTSSynthesisError"]
