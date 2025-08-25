"""
Optionaler Zonos‑Adapter (Stub). Erlaubt sauberen Fallback, wenn Zonos nicht installiert ist.
"""
class ZonosEngine:
    def __init__(self, *_, **__):
        raise ImportError("Zonos TTS nicht installiert")

# Backcompat: einige Stellen erwarten diesen Namen
class ZonosTTSEngine(ZonosEngine):
    pass
