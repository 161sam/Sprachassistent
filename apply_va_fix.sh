#!/usr/bin/env bash
# === apply_va_fix.sh — Repariert Piper/Zonos + Staged‑TTS und finalisiert die CLI ===
set -euo pipefail
cd "$(dirname "$0")"

ts="$(date +%Y%m%d-%H%M%S)"

backup(){ [ -f "$1" ] && cp -f "$1" "$1.bak.$ts" || true; }

echo "1) Sicherungen anlegen…"
backup ws_server/tts/engines/piper.py
backup ws_server/tts/engines/zonos.py
backup ws_server/tts/staged_tts/staged_processor.py
backup config/tts.json
backup sprachassistent/cli.py

echo "2) Echte Engines aus letzten Backups wiederherstellen (Zonos/Piper)…"
restore_latest_backup () {
  local target="$1"
  local latest
  latest="$(ls -1t "$target".bak.* 2>/dev/null | head -n1 || true)"
  if [ -n "${latest}" ] && [ -f "${latest}" ]; then
    echo "   - restore ${target} <= ${latest}"
    cp -f "${latest}" "${target}"
  else
    echo "   ! kein Backup gefunden für ${target} – lasse Datei unverändert"
  fi
}
restore_latest_backup ws_server/tts/engines/zonos.py
restore_latest_backup ws_server/tts/engines/piper.py

echo "3) Staged‑Processor reparieren (kompatible Minimalversion schreiben)…"
cat > ws_server/tts/staged_tts/staged_processor.py <<'PY'
# -*- coding: utf-8 -*-
from __future__ import annotations
import os, logging
from dataclasses import dataclass
from typing import Optional, List, Any
log = logging.getLogger(__name__)

@dataclass
class StagedPlan:
    intro_engine: Optional[str]
    main_engine: Optional[str]
    fast_start: bool = True

def _wrap_chunk(idx: int, total: int, engine: str, res: Any):
    return type("Chunk", (), dict(
        index=idx,
        total=total,
        engine=engine,
        success=getattr(res, "success", False),
        audio_data=getattr(res, "audio_data", None),
        error_message=getattr(res, "error_message", None),
    ))()

class StagedTTSProcessor:
    def __init__(self, manager):
        self.mgr = manager

    def _engine_available_for_voice(self, engine: str, voice: str) -> bool:
        try:
            return (engine in getattr(self.mgr, "engines", {})) and self.mgr.engine_allowed_for_voice(engine, voice)
        except Exception:
            return False

    def _resolve_plan(self, voice: str) -> StagedPlan:
        intro = (os.getenv("STAGED_TTS_INTRO_ENGINE", "piper") or "").strip() or None
        main  = (os.getenv("STAGED_TTS_MAIN_ENGINE",  "zonos") or "").strip() or None
        if intro and not self._engine_available_for_voice(intro, voice):
            log.info("Intro via %s nicht verfügbar → Intro entfällt", intro)
            intro = None
        if main and not self._engine_available_for_voice(main, voice):
            log.warning("Main engine '%s' not available for voice '%s'", main, voice)
            main = None
        return StagedPlan(intro, main, True)

    async def process_staged_tts(self, text: str, voice: str):
        plan = self._resolve_plan(voice)
        chunks: List[Any] = []
        if not plan.intro_engine and not plan.main_engine:
            log.warning("Staged TTS erzeugte keine Chunks (keine Engine verfügbar)")
            return chunks
        if plan.intro_engine:
            e = self.mgr.engines[plan.intro_engine]
            intro_len = max(1, int(os.getenv("STAGED_TTS_MAX_INTRO_LENGTH", "120")))
            res = await e.synthesize(text[:intro_len], voice)
            chunks.append(_wrap_chunk(0, 1 if not plan.main_engine else 2, plan.intro_engine, res))
        if plan.main_engine:
            e = self.mgr.engines[plan.main_engine]
            total = 1 if not plan.intro_engine else 2
            res = await e.synthesize(text, voice)
            chunks.append(_wrap_chunk(0 if not plan.intro_engine else 1, total, plan.main_engine, res))
        return chunks
PY

echo "4) Zonos‑Voicemapping ergänzen/vereinheitlichen…"
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("config/tts.json")
cfg = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
voices = cfg.setdefault("voices", {})
zmap = voices.setdefault("zonos", {})
zmap["de-thorsten-low"] = "thorsten"
zmap["de_DE-thorsten-low"] = "thorsten"
p.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
print("   - Zonos mapping:", zmap)
PY

echo "5) (Optional) Piper‑Model‑Dir/Name hart setzen, damit Resolver greift…"
grep -q '^PIPER_MODEL_DIR=' .env 2>/dev/null || echo "PIPER_MODEL_DIR=$PWD/models/piper" >> .env
grep -q '^PIPER_MODEL_NAME=' .env 2>/dev/null || echo "PIPER_MODEL_NAME=de-thorsten-low.onnx" >> .env
grep -q '^DEFAULT_VOICE=' .env 2>/dev/null || echo "DEFAULT_VOICE=de-thorsten-low" >> .env
# Bypass aus, damit echte Gates wirken:
sed -i 's/^TTS_BYPASS_ENGINE_VOICE_CHECK=.*/TTS_BYPASS_ENGINE_VOICE_CHECK=0/' .env || true
sed -i 's/^ZONOS_ALLOW_ANY_VOICE=.*/ZONOS_ALLOW_ANY_VOICE=0/' .env || true
sed -i 's/^PIPER_ALLOW_ANY_VOICE=.*/PIPER_ALLOW_ANY_VOICE=0/' .env || true

echo "6) Editable neu installieren…"
pip -q install -e .

echo "7) Quick‑Checks:"
echo "   - Plan anzeigen"
va tts-plan || true
echo "   - Direkt‑TTS mit Zonos (schreibt tts_out/once.wav)…"
mkdir -p tts_out
va tts --engine zonos "Probe mit Zonos." --out tts_out/once.wav || true
echo "   - Staged‑TTS (Intro Piper, Main Zonos)…"
va staged "Das ist ein finaler Test für Piper Intro und Zonos Hauptteil." || true

echo "✅ Patch fertig."

