import os
import asyncio
import logging
import importlib
from typing import Optional, Tuple

import numpy as np

log = logging.getLogger(__name__)
_FIRST_MAIN_CALL = True

def _debug_dir() -> str | None:
    try:
        if os.getenv("TTS_DEBUG_DUMP_WAVS", "0").lower() not in ("1","true","yes","on"):
            return None
        import time, os as _os
        d = _os.getenv("TTS_DEBUG_DUMP_DIR")
        if d:
            return d
        ts = str(int(time.time() * 1000))
        d = f"/tmp/tts_debug/{ts}"
        _os.makedirs(d, exist_ok=True)
        _os.environ["TTS_DEBUG_DUMP_DIR"] = d
        return d
    except Exception:
        return None

def _resample_mono(w: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    # Beibehalten für Backups – nicht mehr genutzt (ersetzt durch ratecv)
    if w.size == 0 or sr_in == sr_out:
        return w.astype(np.float32, copy=False)
    ratio = float(sr_out) / float(sr_in)
    n_out = max(1, int(round(w.size * ratio)))
    x_old = np.linspace(0.0, 1.0, w.size, dtype=np.float32)
    x_new = np.linspace(0.0, 1.0, n_out, dtype=np.float32)
    return np.interp(x_new, x_old, w.astype(np.float32)).astype(np.float32)

# ---------- Audio Utils ----------

def _to_float32_mono(buf: Optional[bytes], sr: int) -> tuple[np.ndarray, int]:
    if not buf:
        return np.zeros(0, dtype=np.float32), sr
    a = np.frombuffer(buf, dtype=np.int16).astype(np.float32) / 32767.0
    return a, sr

def _to_int16(x: np.ndarray) -> np.ndarray:
    """Konvertiere float32 [-1..1] → int16 ohne Peak‑Normalisierung.

    Lautheitsanpassung erfolgt ausschließlich im Manager (ein Pfad, konsistent).
    """
    if x.size == 0:
        return x.astype(np.int16)
    y = np.clip(x, -1.0, 1.0)
    return (y * 32767.0).astype(np.int16)

def _fade_join(a: np.ndarray, b: np.ndarray, sr: int, ms: int = 100) -> np.ndarray:
    """Equal‑Power Crossfade mit leichter Headroom (≈‑0.5 dB).

    Vermeidet Pegeldip und minimiert Artefakte beim Engine‑Wechsel.
    """
    if a.size == 0:
        return b
    if b.size == 0:
        return a
    n = max(1, int(sr * ms / 1000))
    n = min(n, a.size, b.size)
    t = np.linspace(0.0, np.pi / 2.0, n, dtype=np.float32)
    win_in = (np.sin(t) ** 2).astype(np.float32)   # b fade‑in
    win_out = (np.cos(t) ** 2).astype(np.float32)  # a fade‑out
    headroom = 0.97
    mid = (a[-n:] * win_out + b[:n] * win_in) * headroom
    return np.concatenate([a[:-n], mid, b[n:]]).astype(np.float32)


def _resample_int16_ratecv(x: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    """Resample float32 mono via audioop.ratecv in int16 domain (HQ, fast)."""
    import audioop
    if sr_in == sr_out or x.size == 0:
        return x.astype(np.float32, copy=False)
    i16 = _to_int16(x)
    y, _ = audioop.ratecv(i16.tobytes(), 2, 1, int(sr_in), int(sr_out), None)
    j = np.frombuffer(y, dtype=np.int16).astype(np.float32) / 32767.0
    return j.astype(np.float32, copy=False)

# ---------- Engine Helpers ----------

def _register_engine(manager, engine_name: str, inst):
    if not hasattr(manager, "engines") or manager.engines is None:
        manager.engines = {}
    manager.engines[engine_name] = inst
    return inst

def _try_manager_methods(manager, engine_name: str):
    for meth in ("get_engine", "ensure_engine", "init_engine", "initialize_engine",
                 "load_engine", "create_engine", "register_engine"):
        fn = getattr(manager, meth, None)
        if callable(fn):
            try:
                got = fn(engine_name) if fn.__code__.co_argcount >= 2 else fn()
            except Exception:
                continue
            if got is not None:
                return got
            eng = getattr(manager, "engines", {}).get(engine_name)
            if eng is not None:
                return eng
    return None

def _direct_import_engine(manager, engine_name: str):
    import inspect
    mod = importlib.import_module(f"ws_server.tts.engines.{engine_name}")
    cand_names = [f"{engine_name.capitalize()}TTSEngine", f"{engine_name.capitalize()}Engine"]
    cls = None
    for nm in cand_names:
        cls = getattr(mod, nm, None)
        if cls is not None:
            break
    if cls is None:
        raise ImportError(f"No engine class found for {engine_name}")
    cfg = getattr(manager, "config", None)
    tried = []
    for args, kwargs in (
        ((cfg,), {}),                # (config)
        ((), {"config": cfg}),       # (config=...)
        ((manager,), {}),            # (manager)
        ((), {}),                    # ()
    ):
        try:
            inst = cls(*args, **kwargs)
            return inst
        except Exception as e:
            tried.append(str(e))
            continue
    raise ImportError(
        f"Could not instantiate {cls.__name__} for {engine_name}; tried variants: " + " | ".join(tried)
    )

def _ensure_engine(manager, engine_name: str):
    eng = getattr(manager, "engines", {}).get(engine_name) if hasattr(manager, "engines") else None
    if eng:
        return eng
    eng = _try_manager_methods(manager, engine_name)
    if eng:
        if engine_name not in getattr(manager, "engines", {}):
            _register_engine(manager, engine_name, eng)
        return eng
    eng = _direct_import_engine(manager, engine_name)
    return _register_engine(manager, engine_name, eng)

# ---------- Manager-first synth ----------

async def _manager_synth(manager, engine_name: str, text: str, voice: str | None) -> Tuple[bytes, int]:
    """
    Bevor wir direkt Engines bauen, probieren wir den Managerweg:
      manager.synthesize(text=..., engine=..., voice=...)
    Rückgabe immer als (bytes, sample_rate).
    """
    for meth in ("synthesize", "synth"):
        fn = getattr(manager, meth, None)
        if callable(fn):
            log.debug("mgr synth call: engine=%s voice=%s text_len=%d", engine_name, voice, len(text or ""))
            res = await fn(text=text, engine=engine_name, voice=voice)
            # TTSResult-kompatibel
            buf = getattr(res, "audio_data", None)
            sr = getattr(res, "sample_rate", 22050)
            if buf:
                log.debug("mgr synth ok: engine=%s bytes=%d sr=%d", engine_name, len(buf), int(sr))
                return (bytes(buf), int(sr))
    raise RuntimeError("manager path unavailable")

async def _synth(manager, engine_name: str, text: str, voice: Optional[str]) -> Tuple[bytes, int]:
    # 1) Manager-Direct (bevorzugt – nutzt Model-Resolver & Voice-Aliases)
    try:
        return await _manager_synth(manager, engine_name, text, voice)
    except Exception:
        pass

    # 2) Engine-Fallback (Lazy-Init + direkte Engine-Synthese)
    eng = _ensure_engine(manager, engine_name)
    if asyncio.iscoroutinefunction(eng.synthesize):
        res = await eng.synthesize(text, voice)
    else:
        res = await asyncio.to_thread(eng.synthesize, text, voice)

    # (bytes, sr)
    if isinstance(res, tuple) and len(res) == 2 and isinstance(res[0], (bytes, bytearray)):
        return (bytes(res[0]), int(res[1]))

    # TTSResult-ähnlich
    buf = getattr(res, "audio_data", None)
    sr = getattr(res, "sample_rate", 22050)
    if buf is None:
        raise RuntimeError(f"Engine '{engine_name}' returned no audio_data")
    log.debug("direct synth ok: engine=%s bytes=%d sr=%d", engine_name, len(buf or b""), int(sr or 0))
    return (buf, int(sr))

# ---------- Public API used by TTSManager ----------

async def synthesize_staged(manager, text: str, voice: Optional[str] = None) -> Tuple[bytes, int]:
    """
    Robuste Staged-Synthese ohne Voice-Caps-Gates:
      - Intro: Engine aus STAGED_TTS_INTRO_ENGINE (default 'piper'), optional
      - Main : Engine aus STAGED_TTS_MAIN_ENGINE  (default 'zonos'), Fallback auf 'piper'
      - Crossfade Intro->Main
    """
    intro_engine = (os.getenv("STAGED_TTS_INTRO_ENGINE", "piper") or "piper").lower()
    main_engine  = (os.getenv("STAGED_TTS_MAIN_ENGINE", "zonos") or "zonos").lower()

    try:
        cross_ms = int(os.getenv("STAGED_TTS_CROSSFADE_MS", "100"))
    except ValueError:
        cross_ms = 100
    try:
        max_intro = int(os.getenv("STAGED_TTS_MAX_INTRO_LENGTH", "150"))
    except ValueError:
        max_intro = 150
    try:
        intro_to = max(1, int(os.getenv("STAGED_TTS_INTRO_TIMEOUT_MS", "2000")))
    except ValueError:
        intro_to = 2000
    try:
        main_to = max(1, int(os.getenv("STAGED_TTS_MAIN_TIMEOUT_MS", "6000")))
    except ValueError:
        main_to = 6000

    intro_text = text[:max_intro]
    pieces: list[tuple[np.ndarray, int]] = []
    # Zielrate: ENV bevorzugt, sonst wird später SR der Haupt‑Engine genommen
    try:
        env_target = int(os.getenv("TTS_TARGET_SR", os.getenv("TTS_OUTPUT_SR", "24000")))
    except Exception:
        env_target = 24000
    target_sr = int(env_target) if env_target else 0

    # Intro (mit Timeout)
    if max_intro > 0:
        try:
            ibuf, isr = await asyncio.wait_for(
                _synth(manager, intro_engine, intro_text, voice),
                timeout=intro_to / 1000.0,
            )
            ia, isr = _to_float32_mono(ibuf, isr)
            pieces.append((ia, isr))
            if not target_sr:
                target_sr = isr
            log.info("StagedTTS: Intro via %s ok (%d bytes @ %d Hz)", intro_engine, len(ibuf), isr)
            # Debug dump
            try:
                dd = _debug_dir()
                if dd:
                    from ws_server.tts.util_wav_dump import write_wav_mono_int16
                    write_wav_mono_int16(f"{dd}/intro_pre.wav", ibuf, isr)
            except Exception:
                pass
        except Exception as e:
            log.warning("StagedTTS: Intro via %s failed (%s) – skipping intro", intro_engine, e)

    # Main (+ Fallback Piper) mit Timeout
    main_ok = False
    global _FIRST_MAIN_CALL
    for cand in (main_engine, "piper"):
        try:
            to = main_to
            if cand == "zonos" and _FIRST_MAIN_CALL:
                try:
                    f = float(os.getenv("STAGED_TTS_FIRST_CALL_FACTOR", "2.0"))
                except Exception:
                    f = 2.0
                to = int(to * max(1.0, f))
                log.info("Erster Aufruf Zonos – Timeout x%.1f", max(1.0, f))
            mbuf, msr = await asyncio.wait_for(
                _synth(manager, cand, text, voice),
                timeout=to / 1000.0,
            )
            ma, msr = _to_float32_mono(mbuf, msr)
            # Zielrate festlegen (falls nicht per ENV)
            if not target_sr:
                target_sr = msr
            if pieces:
                if msr != target_sr:
                    ma = _resample_int16_ratecv(ma, msr, target_sr)
                    msr = target_sr
                a_prev = pieces[-1][0]
                if pieces[-1][1] != target_sr:
                    a_prev = _resample_int16_ratecv(a_prev, pieces[-1][1], target_sr)
                ma = _fade_join(a_prev, ma, target_sr, ms=cross_ms)
                pieces[-1] = (ma, target_sr)
            else:
                if msr != target_sr:
                    ma = _resample_int16_ratecv(ma, msr, target_sr)
                    msr = target_sr
                pieces.append((ma, msr))
            log.info("StagedTTS: Main via %s ok (%d bytes @ %d Hz)", cand, len(mbuf), msr)
            # Debug dump for main and joined (pre-postproc)
            try:
                dd = _debug_dir()
                if dd:
                    from ws_server.tts.util_wav_dump import write_wav_mono_int16
                    write_wav_mono_int16(f"{dd}/main_pre.wav", mbuf, msr)
                    j_i16 = _to_int16(pieces[-1][0]).tobytes()
                    write_wav_mono_int16(f"{dd}/joined_prepostproc.wav", j_i16, target_sr)
            except Exception:
                pass
            main_ok = True
            break
        except Exception as e:
            # Provide extra status when Zonos fails
            if cand == "zonos":
                try:
                    from ws_server.tts.engines.zonos import zonos_status
                    log.warning("StagedTTS: Main via %s failed: %s (%s)", cand, e, zonos_status())
                except Exception:
                    log.warning("StagedTTS: Main via %s failed: %s", cand, e)
            else:
                log.warning("StagedTTS: Main via %s failed: %s", cand, e)
        
    _FIRST_MAIN_CALL = False
    if not pieces or not main_ok:
        # Harter Fallback: kompletter Text via Piper
        try:
            mbuf, msr = await asyncio.wait_for(
                _synth(manager, "piper", text, voice),
                timeout=main_to / 1000.0,
            )
            ma, msr = _to_float32_mono(mbuf, msr)
            if target_sr and msr != target_sr:
                ma = _resample_int16_ratecv(ma, msr, target_sr)
                msr = target_sr
            pieces = [(ma, msr)]
            target_sr = msr
            log.info("StagedTTS: full Piper fallback ok (%d bytes @ %d Hz)", len(mbuf), msr)
        except Exception as e:
            log.error("StagedTTS: complete failure – %s", e)
            return b"", target_sr

    out = pieces[-1][0]
    # joined pre-postproc already dumped above; return raw int16
    return _to_int16(out).tobytes(), target_sr
