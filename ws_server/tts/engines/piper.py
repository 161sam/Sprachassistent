"""Optional re-export of the Piper engine."""

AVAILABLE = False
try:  # pragma: no cover - import may fail
    from backend.tts.piper_tts_engine import *  # type: ignore  # noqa: F401,F403
from ws_server.tts.staged_tts.chunking import sanitize_for_tts
    AVAILABLE = True
except Exception as e:  # pragma: no cover
    IMPORT_ERROR = e  # exposed for diagnostics
    __all__ = []
