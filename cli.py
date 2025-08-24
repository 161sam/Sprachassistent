#!/usr/bin/env python3
# Unified CLI for the project: `va <cmd>`
from __future__ import annotations
import argparse, asyncio, inspect, json, os, sys, pathlib, base64, logging, contextlib
from typing import Optional

# Optional .env
with contextlib.suppress(Exception):
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=".env")  # silently ignored if not installed

logging.basicConfig(level=os.getenv("LOGLEVEL","INFO"),
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("va")

# --- small util ----------------------------------------------------------------
def _read_json(p: pathlib.Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))

def _ensure_dir(p: pathlib.Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def _mk_manager():
    """Create TTSManager with signature-check (compat across branches)."""
    from backend.tts.tts_manager import TTSManager
    cfg = {}
    cfg_path = pathlib.Path("config/tts.json")
    if cfg_path.exists():
        cfg = _read_json(cfg_path)
    sig = inspect.signature(TTSManager.__init__)
    return TTSManager(**({"config": cfg} if "config" in sig.parameters else {}))

async def _init_server():
    """Start unified WebSocket server like desktop does."""
    from ws_server.transport.server import VoiceServer
    from ws_server.metrics.collector import collector
    from ws_server.metrics.http_api import start_http_server
    # Fallback config if dataclass not present
    try:
        from ws_server.core.config import config
        host, port, metrics_port = config.ws_host, config.ws_port, config.metrics_port
    except Exception:
        host = os.getenv("WS_HOST","127.0.0.1")
        port = int(os.getenv("WS_PORT","48231"))
        metrics_port = int(os.getenv("METRICS_PORT","48232"))
    server = VoiceServer()
    await server.initialize()
    collector.start()
    await start_http_server(metrics_port)
    import websockets
    log.info("server listening on %s:%s", host, port)
    async with websockets.serve(server.handle_websocket, host, port,
                                ping_interval=int(os.getenv("PING_INTERVAL","20")),
                                ping_timeout=int(os.getenv("PING_TIMEOUT","10"))):
        log.info("Unified WS-Server listening on ws://%s:%s", host, port)
        log.info("📊 Metrics at :%s", metrics_port)
        await asyncio.Future()

# --- commands ------------------------------------------------------------------
def cmd_env_show(_):
    for k in sorted(os.environ):
        if k.startswith(("WS_", "STT_", "TTS_", "ZONOS_", "PIPER_", "KOKORO_", "LLM_", "ENABLE_","DEFAULT_VOICE","ESPEAKNG_DATA_PATH","PHONEMIZER_ESPEAK_PATH")):
            print(f"{k}={os.environ[k]}")

def cmd_validate_models(_):
    from backend.tts.model_validation import list_voices_with_aliases
    alias_map = list_voices_with_aliases()
    for voice, aliases in alias_map.items():
        print(f"{voice}: {', '.join(aliases)}" if aliases else voice)

async def _tts_once(engine: str, voice: str, text: str, out: pathlib.Path):
    mgr = _mk_manager()
    await mgr.initialize()
    res = await mgr.synthesize(text, engine=engine or None, voice=voice or None)
    if not getattr(res, "success", False) or not getattr(res, "audio_data", b""):
        raise RuntimeError(f"TTS failed: {getattr(res,'error_message', 'unknown')}")
    _ensure_dir(out.parent)
    out.write_bytes(res.audio_data)
    print(f"✅ wrote {out} (sr={getattr(res,'sample_rate',0)})")

def cmd_tts(args):
    text = args.text or "Hallo! Das ist ein Test."
    out = pathlib.Path(args.out)
    asyncio.run(_tts_once(args.engine, args.voice, text, out))

async def _staged(text: str, voice: str, outdir: pathlib.Path):
    mgr = _mk_manager()
    await mgr.initialize()
    from ws_server.tts.staged_tts.staged_processor import StagedTTSProcessor
    proc = StagedTTSProcessor(mgr)
    plan = proc._resolve_plan(voice)
    log.info("Staged plan: intro=%s main=%s voice=%s", plan.intro_engine, plan.main_engine, voice)
    chunks = await proc.process_staged_tts(text, voice)
    if not chunks:
        print("❌ no chunks produced"); return 1
    _ensure_dir(outdir)
    ok=0
    for c in chunks:
        status = "OK" if (c.success and c.audio_data) else f"ERR({c.error_message})"
        print(f"chunk {c.index+1}/{c.total}: {c.engine} | {status}")
        if c.success and c.audio_data:
            (outdir / f"staged_{c.index:02d}_{c.engine}.wav").write_bytes(c.audio_data); ok+=1
    print(("✅" if ok else "❌"), f"WAVs under {outdir}")
    return 0 if ok else 2

def cmd_staged(args):
    text  = args.text or "Hallo! Piper‑Intro, Zonos‑Hauptteil."
    voice = args.voice or os.getenv("DEFAULT_VOICE","de-thorsten-low")
    outdir = pathlib.Path(args.outdir)
    rc = asyncio.run(_staged(text, voice, outdir))
    if rc: sys.exit(rc)

async def _diagnose():
    # Files + JSON sanity
    onnx = pathlib.Path("models/piper/de-thorsten-low.onnx")
    jjs  = pathlib.Path("models/piper/de-thorsten-low.onnx.json")
    print("Piper ONNX:", onnx, onnx.exists(), onnx.stat().st_size if onnx.exists() else 0)
    print("Piper JSON:", jjs,  jjs.exists(),  jjs.stat().st_size  if jjs.exists()  else 0)
    if jjs.exists():
        jj = _read_json(jjs)
        print("  JSON.sample_rate =", jj.get("sample_rate"))
        print("  JSON.phoneme_type =", jj.get("phoneme_type"))
        print("  JSON.espeak.voice =", jj.get("espeak.voice"))
    # Manager & engines
    mgr = _mk_manager()
    try:
        await mgr.initialize()
    except Exception as e:
        print("Manager initialize failed:", e)
        raise
    engines = list(getattr(mgr, "engines", {}).keys())
    print("Engines:", engines)
    for name, eng in getattr(mgr, "engines", {}).items():
        print(" -", name, "| class:", eng.__class__.__name__, "| initialized:", getattr(eng, "is_initialized", None))
    # Piper internal resolve (if method exists)
    piper = getattr(mgr, "engines", {}).get("piper")
    if piper and hasattr(piper, "_resolve_model"):
        try:
            mp, mj = piper._resolve_model("de-thorsten-low")
            print("piper._resolve_model:", mp, mj, "| exist:", pathlib.Path(mp).exists() if mp else None, pathlib.Path(mj).exists() if mj else None)
        except Exception as e:
            print("piper._resolve_model raised:", e)
    # Allowed gates
    from ws_server.tts.staged_tts.staged_processor import StagedTTSProcessor
    from ws_server.tts.voice_utils import canonicalize_voice
    proc = StagedTTSProcessor(mgr)
    for v in ("de-thorsten-low","de_DE-thorsten-low"):
        cv = canonicalize_voice(v)
        def allowed(name):
            with contextlib.suppress(Exception):
                return mgr.engine_allowed_for_voice(name, cv)
            return False
        print(f"voice={v} canonical={cv} | allowed piper={allowed('piper')} zonos={allowed('zonos')}")
        plan = proc._resolve_plan(v)
        print(" plan:", plan)

def cmd_diagnose(_):
    asyncio.run(_diagnose())

def cmd_serve(args):
    # start WS server (same path desktop uses)
    asyncio.run(_init_server())

def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="va", description="Unified CLI for the Voice Assistant")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("serve", help="WS-Server starten (mit Metrics)")
    s.set_defaults(func=cmd_serve)

    s = sub.add_parser("validate", help="TTS-Modelle auflisten/prüfen")
    s.set_defaults(func=cmd_validate_models)

    s = sub.add_parser("env", help="Relevante ENV-Variablen anzeigen")
    s.set_defaults(func=cmd_env_show)

    s = sub.add_parser("tts", help="Einmalige TTS-Synthese (Engine direkt)")
    s.add_argument("--engine", default=os.getenv("TTS_ENGINE","zonos"))
    s.add_argument("--voice",  default=os.getenv("DEFAULT_VOICE","de-thorsten-low"))
    s.add_argument("--out",    default="tts_out/once.wav")
    s.add_argument("text", nargs="?", default=None)
    s.set_defaults(func=cmd_tts)

    s = sub.add_parser("staged", help="Gestufte TTS (Intro+Main) und WAV-Chunks schreiben")
    s.add_argument("--voice",  default=os.getenv("DEFAULT_VOICE","de-thorsten-low"))
    s.add_argument("--outdir", default="tts_out")
    s.add_argument("text", nargs="?", default=None)
    s.set_defaults(func=cmd_staged)

    s = sub.add_parser("diagnose", help="Tiefe Diagnose (Piper/Zonos, Gates, Resolve)")
    s.set_defaults(func=cmd_diagnose)

    args = p.parse_args(argv)
    try:
        args.func(args)
        return 0
    except KeyboardInterrupt:
        return 130
    except SystemExit as e:
        return int(getattr(e, "code", 1))
    except Exception as e:
        log.exception("Command failed: %s", e)
        return 1

if __name__ == "__main__":
    sys.exit(main())
