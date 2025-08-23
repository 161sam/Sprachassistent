"""Thin Piper wrapper that enforces final sanitization."""

from __future__ import annotations

AVAILABLE = False
try:  # Re-export of the backend class
    from backend.tts.piper_tts_engine import PiperTTSEngine as _BasePiperTTSEngine  # type: ignore
    AVAILABLE = True
except Exception as e:  # pragma: no cover
    IMPORT_ERROR = e

try:
    from ws_server.tts.text_sanitizer import pre_clean_for_piper
except Exception:  # pragma: no cover
    def pre_clean_for_piper(text: str) -> str:  # type: ignore
        return text

if AVAILABLE:
    class PiperTTSEngine(_BasePiperTTSEngine):  # type: ignore
        async def synthesize(self, text: str, *args, **kwargs):
            # Final guard before Piper: strips all combining marks
            text = pre_clean_for_piper(text)
            return await super().synthesize(text, *args, **kwargs)

    __all__ = ["PiperTTSEngine", "AVAILABLE"]
else:
    __all__ = ["AVAILABLE"]
