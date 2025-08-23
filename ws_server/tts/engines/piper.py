"""
Wrapper für Piper in der ws_server-Pipeline:
- re-exportiert die Backend-Engine
- entfernt **alle kombinierenden Zeichen** (Mn) + spezielle Troublemaker (z.B. U+0327)
"""
from __future__ import annotations
import re

AVAILABLE = False
try:  # Re-Export der Backend-Klasse
    from backend.tts.piper_tts_engine import PiperTTSEngine as _BasePiperTTSEngine  # type: ignore
    AVAILABLE = True
except Exception as e:  # pragma: no cover
    IMPORT_ERROR = e

# robuster Sanitizer (Fallback; bevorzugt systemweiten)
try:
    from ws_server.tts.text_sanitizer import sanitize_for_tts as _sanitize_for_tts  # type: ignore
except Exception:
    def _sanitize_for_tts(t: str) -> str:
        import unicodedata, re
        t = unicodedata.normalize("NFKC", t)
        # alle kombinierenden Zeichen entfernen (Mn)
        t = "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")
        t = t.replace("\u00A0", " ")
        return " ".join(t.split())

_COMBINING_RE = re.compile(r"[\u0300-\u036F]")
PIPER_PRE_REPLACE_MAP = {
    "\u0327": "",   # combining cedilla – Kern des aktuellen Warnings
}

def _clean_text_for_piper(text: str) -> str:
    t = _sanitize_for_tts(text)
    t = _COMBINING_RE.sub("", t)
    for k, v in PIPER_PRE_REPLACE_MAP.items():
        t = t.replace(k, v)
    return t

if AVAILABLE:
    class PiperTTSEngine(_BasePiperTTSEngine):  # type: ignore
        async def synthesize(self, text: str, *args, **kwargs):
            # **harte** Reinigung direkt vor der eigentlichen Synthese
            text = _clean_text_for_piper(text)
            return await super().synthesize(text, *args, **kwargs)

    __all__ = ["PiperTTSEngine", "AVAILABLE", "PIPER_PRE_REPLACE_MAP"]
else:
    __all__ = ["AVAILABLE"]
