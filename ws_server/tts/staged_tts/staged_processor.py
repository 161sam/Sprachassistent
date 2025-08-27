# (from upload)
# -*- coding: utf-8 -*-
from __future__ import annotations
import os, logging
from dataclasses import dataclass
from typing import Optional, List
log = logging.getLogger(__name__)
@dataclass
class StagedPlan:
    intro_engine: Optional[str]
    main_engine: Optional[str]
    fast_start: bool = True
class StagedTTSProcessor:
    def __init__(self, manager):
        self.mgr = manager
    def _engine_available_for_voice(self, engine: str, voice: str) -> bool:
        # Relaxed check: allow ignoring voice caps (default: on)
        ignore_caps = os.getenv("STAGED_TTS_IGNORE_VOICE_CAPS", "1").lower() in ("1","true","yes","on")
        try:
            if engine not in self.mgr.engines:
                return False
            if ignore_caps:
                return True
            return getattr(self.mgr, "engine_allowed_for_voice", lambda e,v: True)(engine, voice)
        except Exception:
            return engine in getattr(self.mgr, "engines", {})

    def _resolve_plan(self, voice: str) -> StagedPlan:
        intro = (os.getenv("STAGED_TTS_INTRO_ENGINE","piper") or "").strip() or None
        main  = (os.getenv("STAGED_TTS_MAIN_ENGINE","zonos") or "").strip() or None
        if intro and not self._engine_available_for_voice(intro, voice):
            log.info("Intro via %s nicht verfügbar → Intro entfällt", intro); intro = None
        if main and not self._engine_available_for_voice(main, voice):
            log.warning("Main engine '%s' not available for voice '%s'", main, voice); main = None
        return StagedPlan(intro, main, True)
    async def process_staged_tts(self, text: str, voice: str) -> List[object]:
        plan = self._resolve_plan(voice); chunks=[]
        if not plan.intro_engine and not plan.main_engine:
            log.warning("Staged TTS erzeugte keine Chunks (keine Engine verfügbar)"); return chunks
        def _wrap(idx, total, engine, res):
            return type("Chunk", (), dict(index=idx, total=total, engine=engine,
                success=getattr(res,"success",False), audio_data=getattr(res,"audio_data",None),
                error_message=getattr(res,"error_message",None), ))()
        max_intro = int(os.getenv("STAGED_TTS_MAX_INTRO_LENGTH","120"))
        total = (1 if plan.main_engine else 0) + (1 if plan.intro_engine else 0)
        if plan.intro_engine:
            e = self.mgr.engines[plan.intro_engine]
            intro_text = text[:max_intro]
            res = await e.synthesize(intro_text, voice)
            chunks.append(_wrap(0, total, plan.intro_engine, res))
        if plan.main_engine:
            e = self.mgr.engines[plan.main_engine]
            res = await e.synthesize(text, voice)
            idx = 1 if plan.intro_engine else 0
            chunks.append(_wrap(idx, total, plan.main_engine, res))
        return chunks
