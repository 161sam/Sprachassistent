# -*- coding: utf-8 -*-
from __future__ import annotations
import os, json, logging
from typing import Dict, Optional
log = logging.getLogger(__name__)

def _env_true(k: str, default=False) -> bool:
    v = os.getenv(k, "")
    return (v == "" and default) or v.lower() in ("1","true","yes","on")

class TTSManager:
    def __init__(self, *_, **__):
        self.engines: Dict[str, object] = {}
        self.voice_map = self._load_voice_map()

    def _load_voice_map(self) -> Dict[str, Dict[str,str]]:
        try:
            cfg = json.load(open("config/tts.json","r",encoding="utf-8"))
            return cfg.get("voices", {})
        except Exception:
            return {}

    async def initialize(self) -> None:
        planned = os.getenv("TTS_ENGINES","piper,zonos").split(",")
        planned = [e.strip() for e in planned if e.strip()]
        log.info("Geplante TTS-Engines: %s", planned)
        for name in planned:
            try:
                if name == "piper":
                    from ws_server.tts.engines.piper import PiperEngine
                    e = PiperEngine()
                    await e.initialize()
                    self.engines["piper"] = e
                elif name == "zonos":
                    from ws_server.tts.engines.zonos import ZonosEngine
                    e = ZonosEngine()
                    await e.initialize()
                    self.engines["zonos"] = e
                else:
                    log.warning("Unbekannte Engine '%s' wird ignoriert", name)
            except Exception as e:
                log.warning("❌ Engine '%s' nicht verfügbar: %s", name, e)
        if not self.engines:
            log.error("❌ Keine TTS-Engine verfügbar!")
        else:
            log.info("✅ TTS-Manager initialisiert mit %d Engine(s)", len(self.engines))

    def engine_allowed_for_voice(self, engine: str, canonical_voice: str) -> bool:
        if _env_true("TTS_BYPASS_ENGINE_VOICE_CHECK"): return True
        if engine not in self.engines: return False
        if engine == "piper":
            return getattr(self.engines["piper"], "supports_voice")(canonical_voice)
        if engine == "zonos":
            # Stimmen-Mapping in config/tts.json
            zmap = self.voice_map.get("zonos", {})
            return canonical_voice in zmap or _env_true("ZONOS_ALLOW_ANY_VOICE")
        return False

    async def synthesize(self, text: str, engine: Optional[str]=None, voice: Optional[str]=None):
        # Minimaldelegation: nutze angeforderte Engine oder ersten verfügbaren
        if engine and engine in self.engines:
            e = self.engines[engine]
        else:
            e = next(iter(self.engines.values()), None)
            if not e:
                raise RuntimeError("Keine TTS-Engine geladen")
        return await getattr(e, "synthesize")(text, voice)
