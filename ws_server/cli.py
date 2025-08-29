import argparse, os, sys, time, subprocess, urllib.request

__all__ = ["main"]

def _parse_args(argv):
    p = argparse.ArgumentParser(prog="va", description="Sprachassistent CLI (vereinigter Einstiegspunkt)")
    p.add_argument("--validate-models", action="store_true", help="TTS-Modelle prüfen und verfügbare Stimmen anzeigen")
    p.add_argument("--desktop", action="store_true", help="Desktop-App (Electron) zusammen mit Backend starten")
    p.add_argument("--host", default=os.getenv("WS_HOST", os.getenv("BACKEND_HOST", "127.0.0.1")), help="Backend-Host")
    p.add_argument("--port", type=int, default=int(os.getenv("WS_PORT", os.getenv("BACKEND_PORT", "48232"))), help="Backend-Port")
    # TTS/Runtime overrides
    p.add_argument("--tts-progress", choices=["0","1"], help="Terminal‑Progress erzwingen (0/1), überschreibt Config/Env")
    p.add_argument("--zonos-local-dir", help="Lokaler Zonos‑Modellordner (config.json + model.safetensors)")
    p.add_argument("--zonos-model-id", help="HuggingFace Model‑ID für Zonos (z. B. Zyphra/Zonos-v0.1-transformer)")
    p.add_argument("--zonos-speaker", help="Zonos Sprechername (z. B. thorsten)")
    p.add_argument("--language", help="Bevorzugte TTS‑Sprache (z. B. de-DE)")
    return p.parse_args(argv[1:])

def _validate_models():
    try:
        from ws_server.tts.voice_validation import list_voices_with_aliases
        aliases = list_voices_with_aliases() or {}
        for k, v in aliases.items():
            print(f"{k}: {v}")
    except Exception:
        pass
    try:
        from ws_server.tts.engines import available_engines, load_engine
        engines = available_engines()
        for name in sorted(engines):
            try:
                _ = load_engine(name)
                status = "verfügbar/importierbar"
            except Exception as e:
                status = f"nicht verfügbar ({e})"
            print(f"[engine] {name}: {status}")
    except Exception:
        pass

def _spawn_backend_uvicorn(host: str, port: int) -> subprocess.Popen:
    cmd = [sys.executable, "-m", "uvicorn", "ws_server.transport.fastapi_adapter:app", "--host", host, "--port", str(port), "--log-level", "warning"]
    print(f"[va] Starte Backend: {' '.join(cmd)}")
    return subprocess.Popen(cmd, stdout=None, stderr=None)

def _wait_for_health(host: str, port: int, timeout=10.0):
    url = f"http://{host}:{port}/health"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.25)
    return False

def _start_desktop(host: str, port: int):
    be = _spawn_backend_uvicorn(host, port)
    try:
        ok = _wait_for_health(host, port, timeout=12.0)
        if not ok:
            print(f"[va] Warnung: /health {host}:{port} antwortet nicht – fahre fort …")

        env = os.environ.copy()
        env["SKIP_BACKEND_SPAWN"] = "1"
        env["BACKEND_URL"] = f"http://{host}:{port}"
        env["BACKEND_HOST"] = host
        env["BACKEND_PORT"] = str(port)

        cwd = os.path.join(os.getcwd(), "voice-assistant-apps", "desktop")
        # --silent, damit wir nicht vom Electron-Spawn-Log verwirrt werden
        cmd = ["npm", "start", "--silent"]
        print(f"[va] Starte Desktop GUI: {' '.join(cmd)} (cwd={cwd})")
        electron = subprocess.Popen(cmd, cwd=cwd, env=env)
        electron.wait()
    finally:
        try:
            be.terminate(); be.wait(timeout=5)
        except Exception:
            try: be.kill()
            except Exception: pass

def _start_backend_foreground(host: str, port: int):
    os.environ["WS_HOST"] = host
    os.environ["WS_PORT"] = str(port)
    p = _spawn_backend_uvicorn(host, port)
    try:
        p.wait()
    except KeyboardInterrupt:
        pass

def main(argv: list[str] | None = None):
    args = _parse_args(argv or sys.argv)
    # Deprecated path notice when invoked via module
    try:
        if (argv or sys.argv)[0].endswith("ws_server/cli.py") or (argv or sys.argv)[0].endswith("ws_server.cli"):
            print("[va] Hinweis: 'python -m ws_server.cli' ist veraltet. Verwende 'va'.")
    except Exception:
        pass

    # Apply overrides to environment before any subprocess spawn
    if getattr(args, "tts_progress", None):
        os.environ["TTS_PROGRESS"] = args.tts_progress
    if getattr(args, "zonos_local_dir", None):
        os.environ["ZONOS_LOCAL_DIR"] = args.zonos_local_dir
    if getattr(args, "zonos_model_id", None):
        os.environ["ZONOS_MODEL_ID"] = args.zonos_model_id
    if getattr(args, "zonos_speaker", None):
        os.environ["ZONOS_SPEAKER"] = args.zonos_speaker
        # also hint canonical voice
        if not os.getenv("TTS_VOICE") and args.zonos_speaker.lower() == "thorsten":
            os.environ["TTS_VOICE"] = "de-thorsten-low"
    if getattr(args, "language", None):
        os.environ["TTS_LANGUAGE"] = args.language

    if args.validate_models:
        _validate_models(); return
    if args.desktop:
        _start_desktop(args.host, args.port); return
    _start_backend_foreground(args.host, args.port)

if __name__ == "__main__":
    main()
