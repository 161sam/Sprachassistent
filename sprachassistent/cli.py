#!/usr/bin/env python3
"""Unified CLI for the Voice Assistant project."""
from __future__ import annotations
import argparse, asyncio, inspect, json, logging, os, sys, pathlib, contextlib
from typing import Optional

with contextlib.suppress(Exception):
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=".env")

logging.basicConfig(level=os.getenv("LOGLEVEL","INFO"), format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("va")

def _read_json(p: pathlib.Path) -> dict: return json.loads(p.read_text(encoding="utf-8"))
def _ensure_dir(p: pathlib.Path) -> None: p.mkdir(parents=True, exist_ok=True)

def _mk_manager():
    from backend.tts.tts_manager import TTSManager
    cfg = _read_json(pathlib.Path("config/tts.json")) if pathlib.Path("config/tts.json").exists() else {}
    sig = inspect.signature(TTSManager.__init__)
    return TTSManager(**({"config": cfg} if "config" in sig.parameters else {}))

async def _init_server():
    from ws_server.transport.server import VoiceServer
    from ws_server.metrics.collector import collector
    from ws_server.metrics.http_api import start_http_server
    try:
        from ws_server.core.config import config
        host, port, metrics_port = config.ws_host, config.ws_port, config.metrics_port
    except Exception:
        host = os.getenv("WS_HOST","127.0.0.1"); port = int(os.getenv("WS_PORT","48231")); metrics_port = int(os.getenv("METRICS_PORT","48232"))
    server = VoiceServer(); await server.initialize(); collector.start(); await start_http_server(metrics_port)
    import websockets
    log.info("server listening on %s:%s", host, port)
    async with websockets.serve(server.handle_websocket, host, port,
                                ping_interval=int(os.getenv("PING_INTERVAL","20")),
                                ping_timeout=int(os.getenv("PING_TIMEOUT","10"))):
        log.info("Unified WS-Server listening on ws://%s:%s", host, port)
        log.info("📊 Metrics at :%s", metrics_port)
        await asyncio.Future()

def cmd_env(_):
    keys = [k for k in sorted(os.environ) if k.startswith(("WS_","STT_","TTS_","ZONOS_","PIPER_","KOKORO_","LLM_","ENABLE_","DEFAULT_VOICE","ESPEAKNG_DATA_PATH","PHONEMIZER_ESPEAK_PATH"))]
    for k in keys: print(f"{k}={os.environ[k]}")

def cmd_validate(_):
    try:
        from backend.tts.model_validation import list_voices_with_aliases
        alias_map = list_voices_with_aliases()
        for voice, aliases in alias_map.items():
            print(f"{voice}: {', '.join(aliases)}" if aliases else voice)
    except Exception as e:
        log.error("validate failed: %s", e); sys.exit(2)

async def _tts_once(engine: str, voice: str, text: str, out: pathlib.Path):
    mgr = _mk_manager(); await mgr.initialize()
    res = await mgr.synthesize(text, engine=engine or None, voice=voice or None)
    if not getattr(res,"success",False) or not getattr(res,"audio_data",b""):
        raise RuntimeError(f"TTS failed: {getattr(res,'error_message','unknown')}")
    _ensure_dir(out.parent); out.write_bytes(res.audio_data); print(f"✅ wrote {out} (sr={getattr(res,'sample_rate',0)})")

def cmd_tts(a):
    asyncio.run(_tts_once(a.engine, a.voice, a.text or "Hallo! Das ist ein Test.", pathlib.Path(a.out)))

async def _staged(text: str, voice: str, outdir: pathlib.Path):
    from ws_server.tts.staged_tts.staged_processor import StagedTTSProcessor
    mgr = _mk_manager(); await mgr.initialize()
    proc = StagedTTSProcessor(mgr); plan = proc._resolve_plan(voice)
    log.info("Staged plan: intro=%s main=%s voice=%s", plan.intro_engine, plan.main_engine, voice)
    chunks = await proc.process_staged_tts(text, voice)
    if not chunks: print("❌ no chunks produced"); return 1
    _ensure_dir(outdir); ok=0
    for c in chunks:
        status = "OK" if (c.success and c.audio_data) else f"ERR({c.error_message})"
        print(f"chunk {c.index+1}/{c.total}: {c.engine} | {status}")
        if c.success and c.audio_data:
            (outdir / f"staged_{c.index:02d}_{c.engine}.wav").write_bytes(c.audio_data); ok+=1
    print(("✅" if ok else "❌"), f"WAVs under {outdir}"); return 0 if ok else 2

def cmd_staged(a):
    rc = asyncio.run(_staged(a.text or "Hallo! Piper‑Intro, Zonos‑Hauptteil.", a.voice or os.getenv("DEFAULT_VOICE","de-thorsten-low"), pathlib.Path(a.outdir)))
    if rc: sys.exit(rc)

def cmd_tts_plan(a):
    from ws_server.tts.staged_tts.staged_processor import StagedTTSProcessor
    v = a.voice or os.getenv("DEFAULT_VOICE","de-thorsten-low")
    async def run():
        mgr = _mk_manager(); await mgr.initialize()
        proc = StagedTTSProcessor(mgr); plan = proc._resolve_plan(v)
        print(f"Plan voice={v}: intro={plan.intro_engine} main={plan.main_engine} engines={list(mgr.engines.keys())}")
    asyncio.run(run())

def cmd_skills(_):
    try:
        from ws_server.routing.skills import load_skills
        skills = load_skills()
        for s in skills: print(f"- {s.name} (intent={getattr(s,'intent','?')})")
    except Exception as e:
        log.error("skills failed: %s", e); sys.exit(2)

def cmd_route(a):
    utter = a.text or "wie spät ist es?"
    async def run():
        try:
            from ws_server.routing.intent_router import IntentRouter
            r = IntentRouter(); intent, score = r.route(utter)
            print(f"utterance='{utter}' -> intent='{intent}' (score={score:.2f})")
        except Exception as e:
            print("route failed:", e); raise
    asyncio.run(run())

def cmd_llm_probe(a):
    prompt = a.text or "Sag hallo auf Deutsch."
    async def run():
        try:
            from ws_server.core.prompt import call_llm
            resp = await call_llm(prompt)
            print(resp)
        except Exception as e:
            print("llm-probe failed:", e); raise
    asyncio.run(run())

def cmd_serve(_): asyncio.run(_init_server())

def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="va", description="Unified CLI for the Voice Assistant")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("serve", help="WS-Server starten (mit Metrics)");           s.set_defaults(func=cmd_serve)
    s = sub.add_parser("validate", help="TTS-Modelle auflisten/prüfen");           s.set_defaults(func=cmd_validate)
    s = sub.add_parser("env", help="Relevante ENV-Variablen anzeigen");            s.set_defaults(func=cmd_env)
    s = sub.add_parser("tts", help="Einmalige TTS-Synthese (Engine direkt)")
    s.add_argument("--engine", default=os.getenv("TTS_ENGINE","zonos"))
    s.add_argument("--voice",  default=os.getenv("DEFAULT_VOICE","de-thorsten-low"))
    s.add_argument("--out",    default="tts_out/once.wav")
    s.add_argument("text", nargs="?", default=None);                                s.set_defaults(func=cmd_tts)
    s = sub.add_parser("staged", help="Gestufte TTS (Intro+Main) WAV-Chunks");     s.add_argument("--voice",default=os.getenv("DEFAULT_VOICE","de-thorsten-low"))
    s.add_argument("--outdir", default="tts_out"); s.add_argument("text", nargs="?", default=None); s.set_defaults(func=cmd_staged)
    s = sub.add_parser("tts-plan", help="Nur den Staged‑Plan anzeigen");           s.add_argument("--voice", default=None); s.set_defaults(func=cmd_tts_plan)
    s = sub.add_parser("skills", help="Skills auflisten");                          s.set_defaults(func=cmd_skills)
    s = sub.add_parser("route", help="Intent‑Routing testen");                      s.add_argument("text", nargs="?", default=None); s.set_defaults(func=cmd_route)
    s = sub.add_parser("llm-probe", help="LLM‑Anfrage testen");                     s.add_argument("text", nargs="?", default=None); s.set_defaults(func=cmd_llm_probe)

    args = p.parse_args(argv)
    try:
        args.func(args); return 0
    except KeyboardInterrupt: return 130
    except SystemExit as e:   return int(getattr(e, "code", 1))
    except Exception as e:    log.exception("Command failed: %s", e); return 1

if __name__ == "__main__":
    sys.exit(main())
