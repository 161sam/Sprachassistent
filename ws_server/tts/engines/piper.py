"""Optional re-export of the Piper engine."""

AVAILABLE = False
try:  # pragma: no cover - import may fail
    from backend.tts.piper_tts_engine import *  # type: ignore  # noqa: F401,F403
    AVAILABLE = True
except Exception as e:  # pragma: no cover
    IMPORT_ERROR = e  # exposed for diagnostics
    __all__ = []
