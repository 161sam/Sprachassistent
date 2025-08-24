#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

ts="$(date +%Y%m%d-%H%M%S)"

backup() { [ -f "$1" ] && cp -f "$1" "$1.bak.$ts" || true; }

pick_good_backup() {
  # $1 = Zielpfad (ohne .bak), $2 = Regex für "schlechte" (Stub) Dateien
  local base="$1" bad_re="$2"
  # Kandidaten: *.bak* (zeitlich absteigend), außerdem evtl. .bak.sanitize etc.
  # Wir nehmen den ersten, der NICHT den Stub-String enthält.
  for cand in $(ls -1t "${base}".bak* 2>/dev/null || true); do
    if ! grep -qE "$bad_re" "$cand"; then
      echo "$cand"
      return 0
    fi
  done
  return 1
}

echo "1) Backups der aktuellen Dateien anlegen…"
backup ws_server/tts/engines/piper.py
backup ws_server/tts/engines/zonos.py
backup ws_server/tts/staged_tts/staged_processor.py
backup config/tts.json
backup sprachassistent/cli.py

echo "2) Echte Piper/Zonos Engines aus Backups wiederherstellen (keine Stub-Varianten)…"
# Kennzeichner für Stub-Dateien
PIPER_BAD='Piper Stub aktiv|real_synthesize'
ZONOS_BAD='Zonos Stub aktiv|real_synthesize'

# Piper
if cand=$(pick_good_backup ws_server/tts/engines/piper.py "$PIPER_BAD"); then
  echo "   - Piper <= $cand"
  cp -f "$cand" ws_server/tts/engines/piper.py
else
  echo "   ! Achtung: Konnte kein piper.py-Backup ohne Stub finden. Überspringe Restore."
fi

# Zonos
if cand=$(pick_good_backup ws_server/tts/engines/zonos.py "$ZONOS_BAD"); then
  echo "   - Zonos <= $cand"
  cp -f "$cand" ws_server/tts/engines/zonos.py
else
  echo "   ! Achtung: Konnte kein zonos.py-Backup ohne Stub finden. Überspringe Restore."
fi

echo "3) Staged‑Processor (kompatibel & simpel) schreiben…"
cat > ws_server/tts/staged_tts/staged_processor.py <<'PY'
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
        try:
            return (engine in self.mgr.engines) and self.mgr.engine_allowed_for_voice(engine, voice)
        except Exception:
            return False

    def _resolve_plan(self, voice: str) -> StagedPlan:
        intro = (os.getenv("STAGED_TTS_INTRO_ENGINE","piper") or "").strip() or None
        main  = (os.getenv("STAGED_TTS_MAIN_ENGINE","zonos") or "").strip() or None
        if intro and not self._engine_available_for_voice(intro, voice):
            log.info("Intro via %s nicht verfügbar → Intro entfällt", intro)
            intro = None
        if main and not self._engine_available_for_voice(main, voice):
            log.warning("Main engine '%s' not available for voice '%s'", main, voice)
            main = None
        return StagedPlan(intro, main, True)

    async def process_staged_tts(self, text: str, voice: str) -> List[object]:
        plan = self._resolve_plan(voice)
        chunks = []
        if not plan.intro_engine and not plan.main_engine:
            log.warning("Staged TTS erzeugte keine Chunks (keine Engine verfügbar)")
            return chunks

        def _wrap(idx, total, engine, res):
            return type("Chunk", (), dict(
                index=idx, total=total, engine=engine,
                success=getattr(res,"success",False),
                audio_data=getattr(res,"audio_data",None),
                error_message=getattr(res,"error_message",None),
            ))()

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
PY

echo "4) Zonos‑Voicemapping vereinheitlichen…"
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("config/tts.json")
cfg = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
voices = cfg.setdefault("voices", {})
z = voices.setdefault("zonos", {})
z["de-thorsten-low"] = "thorsten"
z["de_DE-thorsten-low"] = "thorsten"
p.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
print("   - Zonos mapping:", z)
PY

echo "5) ENV‑Pins überprüfen/setzen (Piper Model Dir/Name; Staged Engines)…"
upd(){ V="$1"; X="$2"; grep -q "^$V=" .env 2>/dev/null && sed -i "s|^$V=.*|$V=$X|" .env || echo "$V=$X" >> .env; }
upd PIPER_MODEL_DIR  "$PWD/models/piper"
upd PIPER_MODEL_NAME "de-thorsten-low.onnx"
upd STAGED_TTS_INTRO_ENGINE "piper"
upd STAGED_TTS_MAIN_ENGINE  "zonos"
upd TTS_ENGINES "piper,zonos"
# Diese BYPASS-Flags sind nicht mehr nötig – optional entfernen:
# sed -i '/^TTS_BYPASS_ENGINE_VOICE_CHECK=/d;/^PIPER_ALLOW_ANY_VOICE=/d;/^ZONOS_ALLOW_ANY_VOICE=/d' .env || true

echo "6) Editable Reinstall…"
pip -q install -e . >/dev/null

echo "7) Quick‑Checks…"
echo "   - Plan anzeigen"
python3 - <<'PY'
import asyncio, inspect, json, os
from backend.tts.tts_manager import TTSManager
from ws_server.tts.staged_tts.staged_processor import StagedTTSProcessor
sig = inspect.signature(TTSManager.__init__)
mgr = TTSManager(**({"config": json.load(open("config/tts.json"))} if "config" in sig.parameters else {}))
async def run():
    await mgr.initialize()
    proc = StagedTTSProcessor(mgr)
    v = os.getenv("DEFAULT_VOICE","de-thorsten-low")
    plan = proc._resolve_plan(v)
    print(f"Plan voice={v}: intro={plan.intro_engine} main={plan.main_engine} engines={list(mgr.engines.keys())}")
asyncio.run(run())
PY

echo "   - Direkt‑TTS Zonos (schreibt tts_out/once_zonos.wav)…"
python3 - <<'PY'
import asyncio, inspect, json, pathlib
from backend.tts.tts_manager import TTSManager
sig = inspect.signature(TTSManager.__init__)
mgr = TTSManager(**({"config": json.load(open("config/tts.json"))} if "config" in sig.parameters else {}))
async def go():
    await mgr.initialize()
    res = await mgr.synthesize("Nur Zonos bitte.", engine="zonos", voice="de-thorsten-low")
    out = pathlib.Path("tts_out"); out.mkdir(exist_ok=True)
    if getattr(res,"success",False) and getattr(res,"audio_data",b""):
        (out/"once_zonos.wav").write_bytes(res.audio_data)
        print("      OK:", (out/"once_zonos.wav"))
    else:
        print("      FEHLER:", getattr(res,"error_message","unbekannt"))
asyncio.run(go())
PY

echo "   - Gestufte TTS (Intro Piper, Main Zonos)…"
python3 - <<'PY'
import asyncio, inspect, json, os, pathlib
from backend.tts.tts_manager import TTSManager
from ws_server.tts.staged_tts.staged_processor import StagedTTSProcessor
sig = inspect.signature(TTSManager.__init__)
mgr = TTSManager(**({"config": json.load(open("config/tts.json"))} if "config" in sig.parameters else {}))
async def go():
    await mgr.initialize()
    proc = StagedTTSProcessor(mgr)
    chunks = await proc.process_staged_tts("Das ist ein finaler Test für Piper Intro und Zonos Hauptteil.", os.getenv("DEFAULT_VOICE","de-thorsten-low"))
    out = pathlib.Path("tts_out"); out.mkdir(exist_ok=True)
    ok=0
    for c in chunks:
        status="OK" if (c.success and c.audio_data) else f"ERR({c.error_message})"
        print(f"      chunk {c.index+1}/{c.total}: {c.engine} | {status}")
        if c.success and c.audio_data:
            (out/f"staged_{c.index:02d}_{c.engine}.wav").write_bytes(c.audio_data); ok+=1
    print("      ->", ("OK" if ok else "FEHLER"), "Dateien in", out)
asyncio.run(go())
PY

echo "✅ Finaler Patch abgeschlossen."
