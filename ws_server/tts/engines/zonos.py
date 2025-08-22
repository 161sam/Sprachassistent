"""Optional re-export of the Zonos engine."""

AVAILABLE = False
try:  # pragma: no cover - import may fail
    from backend.tts.engine_zonos import *  # type: ignore  # noqa: F401,F403
    AVAILABLE = True
except Exception as e:  # pragma: no cover
    IMPORT_ERROR = e  # exposed for diagnostics
    __all__ = []
