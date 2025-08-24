"""
Optional Zonos TTS engine adapter (Stub).

Wenn die echte Zonos-Implementierung nicht installiert ist,
stellen wir einen Stub bereit, damit der Manager auf Piper zurückfällt.
"""
AVAILABLE = False  # Signal für Manager/CLI

class ZonosEngine:
    def __init__(self, *args, **kwargs):
        raise ImportError("Zonos engine not installed; using Piper fallback")

# Backcompat: manche Stellen importieren ZonosTTSEngine
class ZonosTTSEngine(ZonosEngine):
    pass

def load_engine(*args, **kwargs):
    """API-kompatible Factory."""
    raise ImportError("Zonos engine not installed; using Piper fallback")
