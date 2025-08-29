# ws_server/transport/fastapi_adapter.py
from __future__ import annotations

# GPU/CPU selection
# Do NOT force CPU unless explicitly requested. Honor existing env and ZONOS_DEVICE.
import os as _os
if (_os.getenv("FORCE_CPU", "0").lower() in ("1","true","yes")) or (_os.getenv("ZONOS_DEVICE", "").lower()=="cpu"):
    _os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
else:
    # if user explicitly enables CUDA and nothing set, default to GPU 0
    if _os.getenv("ENABLE_CUDA", "0").lower() in ("1","true","yes") and not _os.getenv("CUDA_VISIBLE_DEVICES"):
        _os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")

import asyncio
import base64
import io
import json
import os
from typing import Dict, Optional, Tuple
import aiohttp

import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import logging as _logging
import sys as _sys
try:
    from ws_server.tts.staged_tts.progress import ProgressRenderer, progress_enabled
except Exception:
    # Fallback no-op implementations
    class ProgressRenderer:  # type: ignore
        def __init__(self, *_a, **_k): pass
        def update(self, *_a, **_k): pass
        def done(self): pass
    def progress_enabled() -> bool:  # type: ignore
        return False

# -----------------------------------------------------------------------------
# FastAPI setup
# -----------------------------------------------------------------------------
def _configure_verbose_logging():
    lvl_name = (os.getenv("WS_LOG_LEVEL") or os.getenv("LOG_LEVEL") or "DEBUG").upper()
    level = getattr(_logging, lvl_name, _logging.DEBUG)
    fmt = os.getenv(
        "WS_LOG_FORMAT",
        "%(asctime)s %(levelname)s [%(name)s:%(lineno)d] %(message)s",
    )

    # Dedicated handler for our namespace to bypass uvicorn's --log-level
    ws_logger = _logging.getLogger("ws_server")
    ws_logger.setLevel(level)
    if not any(isinstance(h, _logging.StreamHandler) and getattr(h, "_ws_custom", False) for h in ws_logger.handlers):
        h = _logging.StreamHandler(_sys.stdout)
        h.setLevel(level)
        h.setFormatter(_logging.Formatter(fmt))
        h._ws_custom = True  # type: ignore[attr-defined]
        ws_logger.addHandler(h)
        ws_logger.propagate = False

    # Raise levels for common libraries
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        try:
            _logging.getLogger(name).setLevel(level)
        except Exception:
            pass

    _logging.captureWarnings(True)


_configure_verbose_logging()
app = FastAPI()
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/handshake")
def handshake():
    _logging.getLogger("ws_server.transport").debug("/api/handshake served")
    return {
        "ok": True,
        "server": "ws_server",
        "version": "dev",
        "features": {"staged_tts": True, "stt": True, "tts": True},
    }


@app.get("/api/tts/status")
def tts_status():
    import os
    info = {
        "cuda_available": False,
        "cuda_device_name": None,
        "cuda_device_count": 0,
        "env": {
            "CUDA_VISIBLE_DEVICES": os.getenv("CUDA_VISIBLE_DEVICES"),
            "ZONOS_DEVICE": os.getenv("ZONOS_DEVICE"),
        },
        "zonos": {
            "importable": False,
            "preferred_device": None,
        },
        "engines": None,
    }
    try:
        import torch  # type: ignore
        info["cuda_available"] = bool(torch.cuda.is_available())
        try:
            info["cuda_device_count"] = int(torch.cuda.device_count())
            if torch.cuda.is_available() and torch.cuda.device_count() > 0:
                info["cuda_device_name"] = torch.cuda.get_device_name(0)
        except Exception:
            pass
    except Exception:
        info["cuda_available"] = False

    try:
        from ws_server.tts.engines.zonos import ZonosEngine  # type: ignore
        info["zonos"]["importable"] = True
        # Preferred device heuristic
        try:
            import torch  # type: ignore
            pref = "cuda" if torch.cuda.is_available() and os.getenv("ZONOS_DEVICE", "").lower() != "cpu" else "cpu"
            info["zonos"]["preferred_device"] = pref
        except Exception:
            pass
    except Exception:
        info["zonos"]["importable"] = False

    try:
        from ws_server.tts.manager import TTSManager
        mgr = TTSManager()
        info["engines"] = {"default": mgr.default_engine, "loaded": list(getattr(mgr, "engines", {}).keys())}
    except Exception:
        pass

    return info


@app.post("/api/spk/upload")
async def upload_speaker_sample(file: UploadFile = File(...), voice_id: str | None = Form(default=None), precompute: str | None = Form(default=None)):
    import os
    from pathlib import Path
    # Validate extension
    allowed = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in allowed:
        return {"ok": False, "error": f"unsupported file type {suffix}"}

    # Determine voice_id
    stem = Path(file.filename or "sample").stem
    if voice_id:
        stem = voice_id.strip()
    # sanitize
    import re
    v_id = re.sub(r"[^a-zA-Z0-9_\-]", "_", stem).strip("_-") or "voice"

    # Destination path
    base = os.getenv("ZONOS_SPEAKER_DIR", "spk_cache")
    base_p = Path(base)
    if not base_p.is_absolute():
        base_p = Path(__file__).resolve().parents[2] / base_p
    base_p.mkdir(parents=True, exist_ok=True)

    dest = base_p / f"{v_id}{suffix}"
    # avoid overwrite
    i = 1
    while dest.exists():
        dest = base_p / f"{v_id}_{i}{suffix}"
        i += 1

    # Save file
    try:
        content = await file.read()
        with open(dest, "wb") as f:
            f.write(content)
    except Exception as e:
        return {"ok": False, "error": f"save failed: {e}"}

    # Optional precompute speaker embedding
    pre_ok = False
    try:
        if precompute and str(precompute).lower() in ("1", "true", "yes"):
            from ws_server.tts.engines.zonos import precompute_speaker_embedding  # type: ignore
            pre_ok = bool(precompute_speaker_embedding(v_id))
    except Exception:
        pre_ok = False

    # Return canonical voice label used by GUI
    canonical = v_id if ("-" in v_id and v_id.split("-",1)[0] in {"de","en","fr","es","it","pt","ru","ja","zh"}) else ("custom-" + v_id)
    return {"ok": True, "voice": canonical, "voice_id": v_id, "path": str(dest), "precomputed": pre_ok}

# ---------------------------- Logging helpers --------------------------------
def _log_term(msg: str):
    try:
        print(msg, flush=True)
    except Exception:
        pass

async def _ws_log(ws: WebSocket, message: str):
    try:
        await ws.send_text(json.dumps({"type": "log", "message": message}))
    except Exception:
        _log_term(f"[log/ws] {message}")

async def _ws_progress(ws: WebSocket, phase: str, index: int, total: int, engine: str):
    try:
        await ws.send_text(json.dumps({
            "type": "progress",
            "phase": phase,
            "index": index,
            "total": total,
            "engine": engine,
        }))
    except Exception:
        _log_term(f"[progress] {phase} {index+1}/{total} via {engine}")
    _logging.getLogger("ws_server.transport").debug(
        "progress: %s %d/%d engine=%s", phase, index + 1, total, engine
    )


# -----------------------------------------------------------------------------
# Helpers (audio utils, STT buffer)
# -----------------------------------------------------------------------------
class STTSession:
    """Buffer für einen Audio‑Stream (int16 mono @ 16kHz)."""

    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self._buf = bytearray()

    def add_chunk_b64_int16(self, b64: str) -> None:
        raw = base64.b64decode(b64)
        self._buf.extend(raw)

    def to_float32(self) -> Tuple[Optional[np.ndarray], int]:
        if not self._buf:
            return None, 0
        arr_i16 = np.frombuffer(self._buf, dtype=np.int16)
        arr_f32 = (arr_i16.astype(np.float32) / 32768.0).copy()
        return arr_f32, self.sample_rate


def _parse_data_url_to_bytes(data_url: str) -> bytes:
    """
    Erwartet z.B. "data:audio/wav;base64,<...>" oder "data:audio/webm;<...>".
    """
    if not data_url.startswith("data:"):
        raise ValueError("not a data URL")
    head, b64 = data_url.split(",", 1)
    if ";base64" not in head:
        from urllib.parse import unquote_to_bytes

        return unquote_to_bytes(b64)
    return base64.b64decode(b64)


def _decode_any_audio_to_float32_mono_16k(raw_bytes: bytes) -> Tuple[np.ndarray, int]:
    """
    Decode audio bytes (webm/ogg/wav) -> np.float32 mono @16k using PyAV.
    """
    try:
        import av  # type: ignore
        from av.audio.resampler import AudioResampler  # type: ignore
    except Exception as e:
        raise RuntimeError(f"PyAV not installed/usable: {e}")

    log = _logging.getLogger("ws_server.audio")
    with av.open(io.BytesIO(raw_bytes)) as container:
        stream = next((s for s in container.streams if s.type == "audio"), None)
        if stream is None:
            raise RuntimeError("no audio stream")
        resampler = AudioResampler(format="s16", layout="mono", rate=16000)
        frames = []
        for packet in container.demux(stream):
            for frame in packet.decode():
                r = resampler.resample(frame)
                if isinstance(r, list):
                    frames.extend([f for f in r if f is not None])
                elif r is not None:
                    frames.append(r)
        if not frames:
            raise RuntimeError("no frames decoded")
        # Robustly extract PCM int16 bytes from frames across PyAV versions
        buf = bytearray()
        for f in frames:
            pl = getattr(f, 'planes', None)
            if not pl:
                continue
            plane0 = pl[0]
            b = b''
            try:
                # Newer PyAV
                b = plane0.to_bytes()  # type: ignore[attr-defined]
            except AttributeError:
                try:
                    # Older PyAV exposes buffer protocol
                    b = bytes(plane0)
                except Exception:
                    try:
                        # Fallback: convert entire frame to ndarray in s16
                        arr = f.to_ndarray(format='s16')  # type: ignore[arg-type]
                        b = arr.tobytes()
                    except Exception:
                        b = b''
            if b:
                buf.extend(b)
        pcm = bytes(buf)
        arr_i16 = np.frombuffer(pcm, dtype=np.int16)
        arr_f32 = (arr_i16.astype(np.float32) / 32768.0).copy()
        log.debug("audio: decoded %d frames -> %d bytes PCM -> %d samples f32", len(frames), len(pcm), len(arr_i16))
        return arr_f32, 16000


# -----------------------------------------------------------------------------
# STT (faster-whisper)
# -----------------------------------------------------------------------------
async def run_faster_whisper(
    arr_f32: Optional[np.ndarray], sr: int, language: str | None = None
) -> str:
    """
    Transcribe using faster-whisper. Gibt "" zurück, wenn nichts decodierbar ist.
    """
    log = _logging.getLogger("ws_server.stt")
    if arr_f32 is None or sr <= 0:
        return ""

    try:
        from faster_whisper import WhisperModel  # type: ignore
    except Exception:
        # Kein fataler Fehler – wir antworten leer.
        return ""

    model_path = os.getenv("FASTER_WHISPER_MODEL", "base")
    # int8 ist ein guter CPU‑Default
    log.debug("whisper: loading model=%s", model_path)
    model = WhisperModel(model_path, compute_type="int8")
    lang = language or os.getenv("STT_LANGUAGE", "de")
    log.debug("whisper: transcribe sr=%d lang=%s len=%.3fs", sr, lang, (len(arr_f32) / sr) if arr_f32 is not None and sr else 0)
    segments, _info = model.transcribe(arr_f32, language=lang, vad_filter=True)
    text = "".join([seg.text for seg in segments]) if segments else ""
    log.debug("whisper: result='%s'", text)
    return (text or "").strip()


# -----------------------------------------------------------------------------
# Optional TTS
# -----------------------------------------------------------------------------
ENABLE_TTS = os.getenv("ENABLE_TTS", "1") == "1"  # default on
_tts_mgr = None


# -----------------------------------------------------------------------------
# Staged‑TTS Runtime Config (overridable by GUI control)
# -----------------------------------------------------------------------------
STAGED_TTS_RUNTIME: Dict[str, object] = {
    "enabled": os.getenv("STAGED_TTS_ENABLED", "1").lower() not in ("0", "false", "no"),
    "intro_engine": os.getenv("STAGED_TTS_INTRO_ENGINE", "piper"),
    "main_engine": os.getenv("STAGED_TTS_MAIN_ENGINE", "zonos"),
    "crossfade_ms": int(os.getenv("STAGED_TTS_CROSSFADE_MS", "100") or 100),
    "max_intro_length": int(os.getenv("STAGED_TTS_MAX_INTRO_LENGTH", "80") or 80),
    "chunked": os.getenv("STAGED_TTS_CHUNKED", "1").lower() not in ("0","false","no"),
    "chunk_size_min": int(os.getenv("STAGED_TTS_CHUNK_SIZE_MIN", "80") or 80),
    "chunk_size_max": int(os.getenv("STAGED_TTS_CHUNK_SIZE_MAX", "180") or 180),
    "main_max_chunks": int(os.getenv("STAGED_TTS_MAIN_MAX_CHUNKS", "6") or 6),
    "intro_chunk_size_max": int(os.getenv("STAGED_TTS_INTRO_CHUNK_SIZE_MAX", "80") or 80),
    "intro_max_chunks": int(os.getenv("STAGED_TTS_INTRO_MAX_CHUNKS", "1") or 1),
}
_logging.getLogger("ws_server.tts.staged").debug(
    "staged runtime: %s",
    {k: STAGED_TTS_RUNTIME[k] for k in sorted(STAGED_TTS_RUNTIME.keys())},
)


async def _ensure_tts_manager():
    global _tts_mgr
    if _tts_mgr is not None:
        return _tts_mgr
    if not ENABLE_TTS:
        return None
    from ws_server.tts.manager import TTSManager

    _logging.getLogger("ws_server.tts").debug("Creating TTSManager …")
    _tts_mgr = TTSManager()
    ok = await _tts_mgr.initialize()
    _logging.getLogger("ws_server.tts").debug(
        "TTSManager initialized: ok=%s engines=%s default=%s",
        ok,
        list(getattr(_tts_mgr, 'engines', {}).keys()),
        getattr(_tts_mgr, 'default_engine', None),
    )
    if not ok:
        _tts_mgr = None
    return _tts_mgr


async def _speak_to_wav_b64(text: str) -> Optional[str]:
    """
    Synthese text -> PCM WAV bytes -> base64. Rückgabe None, falls TTS inaktiv.
    """
    mgr = await _ensure_tts_manager()
    if not mgr:
        return None
    log = _logging.getLogger("ws_server.tts")
    log.debug("speak: single text len=%d", len(text or ""))
    wav = await mgr.synthesize_text(text=text)
    if not wav:
        return None
    log.debug("speak: wav bytes=%d", len(wav))
    return base64.b64encode(wav).decode("ascii")


async def _speak_staged_to_wav_b64(text: str) -> Optional[str]:
    """Synthesize staged TTS (Piper intro + Zonos main) → WAV base64.
    Falls Staged‑TTS deaktiviert ist oder ein Fehler auftritt, gibt None zurück.
    """
    if not STAGED_TTS_RUNTIME.get("enabled", True):
        return None
    mgr = await _ensure_tts_manager()
    if not mgr:
        return None
    # Apply runtime config via environment for the adapter helpers
    os.environ["STAGED_TTS_INTRO_ENGINE"] = str(STAGED_TTS_RUNTIME.get("intro_engine") or "piper")
    os.environ["STAGED_TTS_MAIN_ENGINE"] = str(STAGED_TTS_RUNTIME.get("main_engine") or "zonos")
    os.environ["STAGED_TTS_CROSSFADE_MS"] = str(int(STAGED_TTS_RUNTIME.get("crossfade_ms") or 100))
    os.environ["STAGED_TTS_MAX_INTRO_LENGTH"] = str(int(STAGED_TTS_RUNTIME.get("max_intro_length") or 120))

    try:
        from ws_server.tts.staged_tts.adapter import synthesize_staged
        log = _logging.getLogger("ws_server.tts.staged")
        log.debug("staged: synthesize text len=%d", len(text or ""))
        pcm, sr = await synthesize_staged(mgr, text=text)
        if not pcm:
            return None
        import wave
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(int(sr or 22050))
            wf.writeframes(pcm)
        wav = buf.getvalue()
        b64 = base64.b64encode(wav).decode("ascii")
        log.debug("staged: merged wav bytes=%d sr=%d", len(wav), int(sr or 0))
        return b64
    except Exception:
        return None


async def _speak_staged_chunked_b64(text: str) -> Optional[list[dict]]:
    """Return staged chunks as list of {engine, wav_b64} dicts.
    Uses adapter._synth directly to avoid merging chunks; client will crossfade.
    """
    if not STAGED_TTS_RUNTIME.get("enabled", True):
        return None
    mgr = await _ensure_tts_manager()
    if not mgr:
        return None
    log = _logging.getLogger("ws_server.tts.staged")
    intro_engine = str(STAGED_TTS_RUNTIME.get("intro_engine") or "piper").lower()
    main_engine  = str(STAGED_TTS_RUNTIME.get("main_engine") or "zonos").lower()
    log.debug("staged: chunked intro=%s main=%s text_len=%d", intro_engine, main_engine, len(text or ""))
    show_progress = bool(progress_enabled())
    try:
        max_intro = int(STAGED_TTS_RUNTIME.get("max_intro_length") or 120)
    except Exception:
        max_intro = 120
    # Vorverarbeitung für bessere Prosodie
    try:
        from ws_server.tts.staged_tts.chunking import optimize_for_prosody
        clean_text = optimize_for_prosody(text)
    except Exception:
        clean_text = text
    intro_text = clean_text[:max_intro]
    cmin = int(STAGED_TTS_RUNTIME.get("chunk_size_min") or 80)
    cmax = int(STAGED_TTS_RUNTIME.get("chunk_size_max") or 180)
    main_max = max(1, int(STAGED_TTS_RUNTIME.get("main_max_chunks") or 6))

    def split_main(t: str) -> list[str]:
        # naive sentence/char chunker
        import re
        sentences = re.split(r"(?<=[\.!?])\s+", t.strip())
        parts: list[str] = []
        buf = ""
        for s in sentences:
            s = s.strip()
            if not s:
                continue
            if len(buf) + len(s) + 1 <= cmax:
                buf = (buf + " " + s).strip()
            else:
                if buf:
                    parts.append(buf)
                buf = s
        if buf:
            parts.append(buf)
        # Re-chunk too long parts
        out: list[str] = []
        for p in parts:
            if len(p) <= cmax:
                out.append(p)
            else:
                i = 0
                while i < len(p):
                    out.append(p[i:i+cmax])
                    i += cmax
        # merge too small parts
        merged: list[str] = []
        acc = ""
        for p in out:
            if len(acc) + len(p) + 1 < cmin:
                acc = (acc + " " + p).strip()
            else:
                if acc:
                    merged.append(acc)
                    acc = ""
                merged.append(p)
        if acc:
            merged.append(acc)
        out_final = merged[:main_max]
        log.debug("staged: chunked main parts=%d (cmin=%d cmax=%d)", len(out_final), cmin, cmax)
        return out_final

    from ws_server.tts.staged_tts.adapter import _synth as _adapter_synth
    chunks: list[dict] = []
    import wave

    # Try intro first (optional) and chunk it for faster start
    if intro_text and intro_engine:
        try:
            icmax = int(STAGED_TTS_RUNTIME.get("intro_chunk_size_max") or 80)
            imax = int(STAGED_TTS_RUNTIME.get("intro_max_chunks") or 2)
            intro_parts = []
            i = 0
            while i < len(intro_text) and len(intro_parts) < imax:
                intro_parts.append(intro_text[i:i+icmax]); i += icmax
            pr_intro = ProgressRenderer("intro", max(1, len(intro_parts)), enabled=show_progress)
            for idx, part in enumerate(intro_parts):
                # progress: intro
                try: await _ws_progress(_ws_progress.ws, "intro", idx, len(intro_parts), intro_engine)  # type: ignore[attr-defined]
                except Exception: pass
                ibuf, isr = await asyncio.wait_for(_adapter_synth(mgr, intro_engine, part, None), timeout=5.0)
                log.debug("staged: intro part %d/%d bytes=%d sr=%d", idx+1, len(intro_parts), len(ibuf or b""), int(isr or 0))
                buf = io.BytesIO()
                with wave.open(buf, "wb") as wf:
                    wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(int(isr or 22050)); wf.writeframes(ibuf)
                chunks.append({"engine": intro_engine, "wav_b64": base64.b64encode(buf.getvalue()).decode("ascii"), "text": part})
                pr_intro.update(idx + 1)
            pr_intro.done()
        except Exception:
            pass

    # Main in mehrere Teile (Latenz runter)
    main_parts = split_main(clean_text)
    selected = None
    main_parts_total = len(main_parts) if main_parts else 0
    for cand in (main_engine, "piper"):
        try:
            # Probeklang generieren, um engine zu testen
            _mbuf, _msr = await asyncio.wait_for(_adapter_synth(mgr, cand, main_parts[0] if main_parts else text, None), timeout=10.0)
            log.debug("staged: main engine selected=%s probe_bytes=%d sr=%d", cand, len(_mbuf or b""), int(_msr or 0))
            selected = (cand, _msr)
            # Erstes Stück direkt senden
            buf = io.BytesIO();
            with wave.open(buf, "wb") as wf:
                wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(int(_msr or 22050)); wf.writeframes(_mbuf)
            chunks.append({"engine": cand, "wav_b64": base64.b64encode(buf.getvalue()).decode("ascii"), "text": main_parts[0] if main_parts else text})
            break
        except Exception:
            continue
    if selected:
        cand, msr = selected
        # restliche Teile generieren
        rest = main_parts[1:] if main_parts else []
        pr_main = ProgressRenderer("main ", max(1, main_parts_total), enabled=show_progress)
        if main_parts_total:
            try: pr_main.update(1)
            except Exception: pass
        for idx, part in enumerate(rest, start=1):
            try:
                # progress: main
                try: await _ws_progress(_ws_progress.ws, "main", idx, len(main_parts), cand)  # type: ignore[attr-defined]
                except Exception: pass
                mbuf, msr2 = await asyncio.wait_for(_adapter_synth(mgr, cand, part, None), timeout=30.0)
                log.debug("staged: main part %d/%d bytes=%d sr=%d", idx+1, len(main_parts), len(mbuf or b""), int(msr2 or 0))
                buf2 = io.BytesIO();
                with wave.open(buf2, "wb") as wf:
                    wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(int(msr2 or 22050)); wf.writeframes(mbuf)
                chunks.append({"engine": cand, "wav_b64": base64.b64encode(buf2.getvalue()).decode("ascii"), "text": part})
                pr_main.update(idx + 1)
            except Exception:
                # wenn ein Part fehlschlägt: weiter, rest kommt trotzdem
                continue
        pr_main.done()

    return chunks or None


# -----------------------------------------------------------------------------
# LLM Runtime Config
# -----------------------------------------------------------------------------
LLM_RUNTIME: Dict[str, object] = {
    "provider": os.getenv("LLM_PROVIDER", "lmstudio"),  # 'lmstudio' or 'openai'
    "api_base": os.getenv("LLM_API_BASE", "http://127.0.0.1:1234/v1"),
    "api_key": os.getenv("OPENAI_API_KEY", ""),
    "model": os.getenv("LLM_DEFAULT_MODEL", "gpt-3.5-turbo"),
    "temperature": float(os.getenv("LLM_TEMPERATURE", "0.7")),
    "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "256")),
    "system_prompt": os.getenv("LLM_SYSTEM_PROMPT", "You are a helpful assistant."),
}

async def _llm_list_models() -> Dict[str, object]:
    base = str(LLM_RUNTIME.get("api_base") or "").rstrip("/")
    provider = str(LLM_RUNTIME.get("provider") or "lmstudio").lower()
    url = f"{base}/models"
    headers = {}
    if provider == "openai":
        key = str(LLM_RUNTIME.get("api_key") or "").strip()
        headers["Authorization"] = f"Bearer {key}"
    else:
        headers["Authorization"] = "Bearer lm-studio"

    try:
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.get(url, headers=headers) as resp:
                data = await resp.json()
                models = data.get("data") or data.get("models") or []
                ids = []
                for m in models:
                    if isinstance(m, dict) and m.get("id"):
                        ids.append(m["id"])
                    elif isinstance(m, str):
                        ids.append(m)
                return {"models": ids, "current": LLM_RUNTIME.get("model")}
    except Exception:
        return {"models": [], "current": LLM_RUNTIME.get("model")}

async def _llm_chat(user_text: str) -> Optional[str]:
    base = str(LLM_RUNTIME.get("api_base") or "").rstrip("/")
    provider = str(LLM_RUNTIME.get("provider") or "lmstudio").lower()
    url = f"{base}/chat/completions"
    model = str(LLM_RUNTIME.get("model") or "gpt-3.5-turbo")
    temp = float(LLM_RUNTIME.get("temperature") or 0.7)
    max_tokens = int(LLM_RUNTIME.get("max_tokens") or 256)
    sys_prompt = str(LLM_RUNTIME.get("system_prompt") or "")
    # Optional: couple LLM answer language to TTS_LANGUAGE
    try:
        if os.getenv("LINK_LLM_TO_TTS_LANGUAGE", "0").lower() in ("1","true","yes","on"):
            tts_lang = (os.getenv("TTS_LANGUAGE") or "").lower()
            if tts_lang.startswith("de"):
                if not sys_prompt:
                    sys_prompt = "Bitte antworte auf Deutsch in kurzen, gesprochenen Sätzen. Keine Listen oder Markdown."
            # (extendable for other locales)
    except Exception:
        pass
    headers = {"Content-Type": "application/json"}
    if provider == "openai":
        key = str(LLM_RUNTIME.get("api_key") or "").strip()
        headers["Authorization"] = f"Bearer {key}"
    else:
        headers["Authorization"] = "Bearer lm-studio"
    payload = {
        "model": model,
        "messages": ([{"role": "system", "content": sys_prompt}] if sys_prompt else []) + [
            {"role": "user", "content": user_text}
        ],
        "temperature": temp,
        "max_tokens": max_tokens,
        "stream": False,
    }
    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.post(url, headers=headers, json=payload) as resp:
                data = await resp.json()
                # LM Studio and OpenAI compatible schema
                choices = data.get("choices") or []
                if choices and choices[0] and choices[0].get("message"):
                    return choices[0]["message"].get("content")
    except Exception:
        pass
    return None

# -----------------------------------------------------------------------------
# GUI Control Handlers (LLM/TTS Settings, Tests)
# -----------------------------------------------------------------------------
async def _handle_gui_control(ws: WebSocket, payload: dict) -> bool:
    """
    Sehr einfache Handler für GUI-Events:
      - tts_test: erzeugt WAV und sendet {"type":"tts","format":"wav_base64","audio":...}
      - get_llm_models: liefert Dummy-Liste
      - switch_llm_model / set_llm_options: quittiert
      - switch_tts_engine / set_tts_voice / set_tts_options: quittiert
      - staged_tts_control / set_stt_options / clear_cache: quittieren
    """
    typ = payload.get("type")

    # --- TTS Test
    if typ == "tts_test":
        text = payload.get("content") or payload.get("text") or "Test 1 2 3."
        try:
            b64wav = await _speak_to_wav_b64(text)
            if b64wav:
                await ws.send_text(
                    json.dumps({"type": "tts", "format": "wav_base64", "audio": b64wav})
                )
                await ws.send_text(json.dumps({"type": "response", "content": text}))
            else:
                await ws.send_text(
                    json.dumps(
                        {"type": "error", "message": "TTS nicht aktiv (ENABLE_TTS=1?)"}
                    )
                )
        except Exception as e:
            await ws.send_text(
                json.dumps({"type": "error", "message": f"tts_test failed: {e}"})
            )
        return True

    # --- LLM Dummies
    if typ == "get_llm_models":
        info = await _llm_list_models()
        await ws.send_text(json.dumps({"type": "llm_models", **info}))
        return True

    if typ == "switch_llm_model":
        m = (payload.get("model") or "").strip()
        if m:
            LLM_RUNTIME["model"] = m
        await ws.send_text(json.dumps({"type": "llm_model_switched", "model": LLM_RUNTIME.get("model")}))
        return True

    if typ == "set_llm_provider":
        prov = (payload.get("provider") or LLM_RUNTIME.get("provider") or "lmstudio").lower()
        base = payload.get("api_base") or LLM_RUNTIME.get("api_base")
        key = payload.get("api_key") if payload.get("api_key") is not None else LLM_RUNTIME.get("api_key")
        LLM_RUNTIME.update({"provider": prov, "api_base": base, "api_key": key})
        await ws.send_text(json.dumps({"type": "llm_provider_updated", **LLM_RUNTIME}))
        return True

    if typ == "set_llm_options":
        if "temperature" in payload:
            try: LLM_RUNTIME["temperature"] = float(payload.get("temperature"))
            except Exception: pass
        if "max_tokens" in payload:
            try: LLM_RUNTIME["max_tokens"] = int(payload.get("max_tokens"))
            except Exception: pass
        if "system_prompt" in payload:
            LLM_RUNTIME["system_prompt"] = str(payload.get("system_prompt") or "")
        await ws.send_text(json.dumps({"type": "llm_opts_updated", "temperature": LLM_RUNTIME["temperature"], "max_tokens": LLM_RUNTIME["max_tokens"]}))
        return True

    # --- TTS/STT Settings + staged tts (nur Acks for now)
    if typ in (
        "switch_tts_engine",
        "set_tts_voice",
        "set_tts_language",
        "set_tts_options",
        "staged_tts_control",
        "set_stt_options",
        "clear_cache",
    ):
        # (removed) dynamic voice listing; GUI must rely on static list

        # Apply immediate TTS config changes where trivial
        if typ == "set_tts_voice":
            v = (payload.get("voice") or payload.get("tts_voice") or "").strip()
            if v:
                os.environ["TTS_VOICE"] = v
                mgr = await _ensure_tts_manager()
                if mgr and getattr(mgr, "config", None) is not None:
                    try:
                        mgr.config.voice = v
                    except Exception:
                        pass
                # Propagate to all engines to keep Piper/Zonos in sync
                if mgr and getattr(mgr, "engines", None):
                    try:
                        from ws_server.tts.manager import TTSEngineType
                        for name in list(mgr.engines.keys()):
                            try:
                                await mgr.set_voice(v, TTSEngineType(name))
                            except Exception:
                                # fallback: set attribute directly
                                try: mgr.engines[name].config.voice = v  # type: ignore[attr-defined]
                                except Exception: pass
                    except Exception:
                        pass
        if typ == "set_tts_options":
            mgr = await _ensure_tts_manager()
            if mgr and getattr(mgr, "config", None) is not None:
                spd = payload.get("speed")
                vol = payload.get("volume")
                try:
                    if spd is not None:
                        mgr.config.speed = float(spd)
                except Exception:
                    pass
                try:
                    if vol is not None:
                        mgr.config.volume = float(vol)
                except Exception:
                    pass
        if typ == "set_tts_language":
            # accepts BCP-47 like 'de-DE'; engines handle mapping internally
            lang = (payload.get("value") or payload.get("language") or payload.get("lang") or "").strip()
            if lang:
                os.environ["TTS_LANGUAGE"] = lang
                # also set engine-specific hints for Zonos
                os.environ["ZONOS_LANG"] = lang
                os.environ["ZONOS_LANGUAGE"] = lang
                mgr = await _ensure_tts_manager()
                if mgr and getattr(mgr, "config", None) is not None:
                    try:
                        mgr.config.language = lang
                    except Exception:
                        pass
        # staged_tts_control may include direct config (without action)
        if typ == "staged_tts_control":
            cfg = payload or {}
            if any(k in cfg for k in ("enabled", "intro_engine", "main_engine", "intro_length", "crossfade_ms", "chunked", "chunk_size_min", "chunk_size_max", "main_max_chunks")):
                if "enabled" in cfg:
                    STAGED_TTS_RUNTIME["enabled"] = bool(cfg.get("enabled"))
                if "intro_engine" in cfg:
                    STAGED_TTS_RUNTIME["intro_engine"] = str(cfg.get("intro_engine") or "piper")
                if "main_engine" in cfg:
                    STAGED_TTS_RUNTIME["main_engine"] = str(cfg.get("main_engine") or "zonos")
                if "intro_length" in cfg:
                    try:
                        STAGED_TTS_RUNTIME["max_intro_length"] = int(cfg.get("intro_length"))
                    except Exception:
                        pass
                if "crossfade_ms" in cfg:
                    try:
                        STAGED_TTS_RUNTIME["crossfade_ms"] = int(cfg.get("crossfade_ms"))
                    except Exception:
                        pass
                if "chunked" in cfg:
                    STAGED_TTS_RUNTIME["chunked"] = bool(cfg.get("chunked"))
                if "chunk_size_min" in cfg:
                    try: STAGED_TTS_RUNTIME["chunk_size_min"] = int(cfg.get("chunk_size_min"))
                    except Exception: pass
                if "chunk_size_max" in cfg:
                    try: STAGED_TTS_RUNTIME["chunk_size_max"] = int(cfg.get("chunk_size_max"))
                    except Exception: pass
                if "main_max_chunks" in cfg:
                    try: STAGED_TTS_RUNTIME["main_max_chunks"] = int(cfg.get("main_max_chunks"))
                    except Exception: pass
                await ws.send_text(
                    json.dumps(
                        {
                            "type": "staged_tts_config_updated",
                            "config": {
                                "enabled": STAGED_TTS_RUNTIME["enabled"],
                                "intro_engine": STAGED_TTS_RUNTIME["intro_engine"],
                                "main_engine": STAGED_TTS_RUNTIME["main_engine"],
                                "max_intro_length": STAGED_TTS_RUNTIME["max_intro_length"],
                                "crossfade_ms": STAGED_TTS_RUNTIME["crossfade_ms"],
                                "chunked": STAGED_TTS_RUNTIME["chunked"],
                                "chunk_size_min": STAGED_TTS_RUNTIME["chunk_size_min"],
                                "chunk_size_max": STAGED_TTS_RUNTIME["chunk_size_max"],
                                "main_max_chunks": STAGED_TTS_RUNTIME["main_max_chunks"],
                            },
                        }
                    )
                )
                return True
        if typ == "set_stt_options":
            lang = (payload.get("language") or os.getenv("STT_LANGUAGE") or "de").strip()
            os.environ["STT_LANGUAGE"] = lang
            await ws.send_text(json.dumps({"type":"ok","action":"set_stt_options","language":lang}))
            return True
        await ws.send_text(json.dumps({"type": "ok", "action": typ}))
        return True

    return False


# -----------------------------------------------------------------------------
# WebSocket
# -----------------------------------------------------------------------------
@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    _log = _logging.getLogger("ws_server.ws")
    _log.debug("WebSocket accepted from client")
    stream_sessions: Dict[str, STTSession] = {}
    # bind ws to progress helper (weakly)
    try:
        _ws_progress.ws = ws  # type: ignore[attr-defined]
    except Exception:
        pass

    try:
        while True:
            msg = await ws.receive()
            if "text" in msg and msg["text"]:
                _log.debug("ws: received text len=%d", len(msg["text"]))
            elif "bytes" in msg and msg["bytes"] is not None:
                _log.debug("ws: received %d bytes (ignored path)", len(msg["bytes"]))

            # (Optional) Binary Pfad (für später)
            if "bytes" in msg and msg["bytes"] is not None:
                # aktuell ignorieren
                continue

            data = msg.get("text")
            if not data:
                continue

            try:
                payload = json.loads(data)
            except Exception:
                # Ungültiges JSON ignorieren
                continue

            # Handshake
            if payload.get("op") == "hello":
                _log.debug("handshake received: %s", payload)
                bin_ok = os.getenv("WS_BINARY_AUDIO", "0").lower() in ("1","true","yes","on")
                resp = {
                    "op": "ready",
                    "capabilities": {
                        "binaryAudio": bool(bin_ok),
                        "staged_tts": True,
                        "stt": True,
                        "tts": ENABLE_TTS,
                    },
                    "stream_id": payload.get("stream_id"),
                }
                await ws.send_text(json.dumps(resp))
                continue

            typ = payload.get("type")

            # Zuerst GUI-Control Events abfangen
            handled = await _handle_gui_control(ws, payload)
            if handled:
                continue

            # Ping/Pong
            if typ == "ping":
                _log.debug("ping received: %s", payload)
                ts = payload.get("timestamp") or payload.get("client_timestamp")
                await ws.send_text(json.dumps({"type": "pong", "client_timestamp": ts}))
                continue

            # --- Streaming STT (int16 base64 chunks) ---
            if typ == "start_audio_stream":
                sid = payload.get("stream_id") or "s"
                sr = payload.get("config", {}).get("sampleRate", 16000)
                stream_sessions[sid] = STTSession(sample_rate=sr)
                _log.debug("audio stream started: id=%s sr=%d", sid, sr)
                await ws.send_text(
                    json.dumps({"type": "audio_stream_started", "stream_id": sid})
                )
                continue

            if typ == "audio_chunk":
                sid = payload.get("stream_id") or "s"
                sess = stream_sessions.setdefault(sid, STTSession())
                b64 = payload.get("chunk")
                if b64:
                    sess.add_chunk_b64_int16(b64)
                    _log.debug("audio chunk: id=%s size_b64=%d total_bytes=%d", sid, len(b64), len(sess._buf))
                continue

            if typ == "end_audio_stream":
                sid = payload.get("stream_id") or "s"
                sess = stream_sessions.pop(sid, None)
                if not sess:
                    await ws.send_text(
                        json.dumps({"type": "audio_stream_ended", "stream_id": sid})
                    )
                    continue
                arr_f32, sr = sess.to_float32()
                _log.debug("audio stream end: id=%s frames=%d sr=%d", sid, 0 if arr_f32 is None else len(arr_f32), sr)
                text = await run_faster_whisper(arr_f32, sr)
                _log.debug("stt result: '%s'", text)
                reply = await _llm_chat(text) or text or ""
                _log.debug("llm reply: '%s'", reply)
                await ws.send_text(json.dumps({"type": "response", "content": reply or "(leer)"}))
                # optionaler TTS‑Rundlauf
                if ENABLE_TTS and reply:
                    if STAGED_TTS_RUNTIME.get("enabled", True) and STAGED_TTS_RUNTIME.get("chunked", True):
                        seq = os.urandom(8).hex()
                        chunks = await _speak_staged_chunked_b64(reply)
                        if chunks:
                            total = len(chunks)
                            for idx, ch in enumerate(chunks):
                                await ws.send_text(json.dumps({
                                    "type": "tts_chunk",
                                    "sequence_id": seq,
                                    "index": idx,
                                    "total": total,
                                    "engine": ch.get("engine"),
                                    "text": ch.get("text"),
                                    "audio": ch.get("wav_b64"),
                                }))
                            await ws.send_text(json.dumps({"type":"tts_sequence_end", "sequence_id": seq}))
                        else:
                            b64wav = await _speak_staged_to_wav_b64(reply) or await _speak_to_wav_b64(reply)
                            if b64wav:
                                await ws.send_text(json.dumps({"type": "tts", "format": "wav_base64", "audio": b64wav}))
                    else:
                        b64wav = await _speak_staged_to_wav_b64(reply) or await _speak_to_wav_b64(reply)
                        if b64wav:
                            await ws.send_text(json.dumps({"type": "tts", "format": "wav_base64", "audio": b64wav}))
                await ws.send_text(
                    json.dumps({"type": "audio_stream_ended", "stream_id": sid})
                )
                continue

            # --- Single‑shot Data:URL Upload (Electron/Browser convenience) ---
            if typ == "audio":
                content = payload.get("content", "")
                try:
                    raw = _parse_data_url_to_bytes(content)
                    arr_f32, sr = _decode_any_audio_to_float32_mono_16k(raw)
                    _log.debug("upload audio decoded: samples=%d sr=%d", len(arr_f32), sr)
                    text = await run_faster_whisper(arr_f32, sr)
                    _log.debug("stt result: '%s'", text)
                    await ws.send_text(
                        json.dumps({"type": "response", "content": text or "(leer)"})
                    )
                    if ENABLE_TTS and text:
                        if STAGED_TTS_RUNTIME.get("enabled", True) and STAGED_TTS_RUNTIME.get("chunked", True):
                            seq = os.urandom(8).hex()
                            chunks = await _speak_staged_chunked_b64(text)
                            if chunks:
                                total = len(chunks)
                                for idx, ch in enumerate(chunks):
                                    await ws.send_text(json.dumps({
                                        "type": "tts_chunk",
                                        "sequence_id": seq,
                                        "index": idx,
                                        "total": total,
                                        "engine": ch.get("engine"),
                                        "text": ch.get("text"),
                                        "audio": ch.get("wav_b64"),
                                    }))
                                await ws.send_text(json.dumps({"type":"tts_sequence_end", "sequence_id": seq}))
                            else:
                                b64wav = await _speak_staged_to_wav_b64(text) or await _speak_to_wav_b64(text)
                                if b64wav:
                                    await ws.send_text(json.dumps({
                                        "type": "tts",
                                        "format": "wav_base64",
                                        "audio": b64wav,
                                    }))
                        else:
                            b64wav = await _speak_staged_to_wav_b64(text) or await _speak_to_wav_b64(text)
                            if b64wav:
                                await ws.send_text(json.dumps({
                                    "type": "tts",
                                    "format": "wav_base64",
                                    "audio": b64wav,
                                }))
                except Exception as e:
                    await ws.send_text(
                        json.dumps(
                            {"type": "error", "message": f"audio decode failed: {e}"}
                        )
                    )
                continue

            # --- Text‑Roundtrip (LLM integration + optional TTS) ---
            if typ == "text":
                content = payload.get("content", "")
                _log.debug("text message: '%s'", content)
                reply = await _llm_chat(content) or content
                _log.debug("llm reply: '%s'", reply)
                await ws.send_text(json.dumps({"type": "response", "content": reply}))
                if ENABLE_TTS and content:
                    if STAGED_TTS_RUNTIME.get("enabled", True) and STAGED_TTS_RUNTIME.get("chunked", True):
                        seq = os.urandom(8).hex()
                        chunks = await _speak_staged_chunked_b64(reply)
                        if chunks:
                            total = len(chunks)
                            for idx, ch in enumerate(chunks):
                                await ws.send_text(json.dumps({
                                    "type": "tts_chunk",
                                    "sequence_id": seq,
                                    "index": idx,
                                    "total": total,
                                    "engine": ch.get("engine"),
                                    "text": ch.get("text"),
                                    "audio": ch.get("wav_b64"),
                                }))
                            await ws.send_text(json.dumps({"type":"tts_sequence_end", "sequence_id": seq}))
                        else:
                            b64wav = await _speak_staged_to_wav_b64(reply) or await _speak_to_wav_b64(reply)
                            if b64wav:
                                await ws.send_text(json.dumps({"type": "tts", "format": "wav_base64", "audio": b64wav}))
                    else:
                        b64wav = await _speak_staged_to_wav_b64(reply) or await _speak_to_wav_b64(reply)
                        if b64wav:
                            await ws.send_text(json.dumps({"type": "tts", "format": "wav_base64", "audio": b64wav}))
                continue

    except WebSocketDisconnect:
        _logging.getLogger("ws_server.ws").debug("WebSocket disconnected")
    except Exception as e:
        try:
            await ws.send_text(json.dumps({"type": "error", "message": str(e)}))
        except Exception:
            pass
