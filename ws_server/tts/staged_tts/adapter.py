import os
import asyncio
import logging
import importlib
from typing import Optional, Tuple

import numpy as np

log = logging.getLogger(__name__)

def _resample_mono(w: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    if w.size == 0 or sr_in == sr_out:
        return w.astype(np.float32, copy=False)
    # einfacher linearer Resampler
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
    if x.size == 0:
        return x.astype(np.int16)
    m = max(1e-9, float(np.max(np.abs(x))))
    y = np.clip(x / m, -1.0, 1.0)
    return (y * 32767.0).astype(np.int16)

def _fade_join(a: np.ndarray, b: np.ndarray, sr: int, ms: int = 60) -> np.ndarray:
    if a.size == 0:
        return b
    if b.size == 0:
        return a
    n = max(1, int(sr * ms / 1000))
    n = min(n, a.size, b.size)
    fade = np.linspace(0.0, 1.0, n, dtype=np.float32)
    return np.concatenate([a[:-n], a[-n:] * (1.0 - fade) + b[:n] * fade, b[n:]]).astype(np.float32)

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
            res = await fn(text=text, engine=engine_name, voice=voice)
            # TTSResult-kompatibel
            buf = getattr(res, "audio_data", None)
            sr = getattr(res, "sample_rate", 22050)
            if buf:
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
        cross_ms = int(os.getenv("STAGED_TTS_CROSSFADE_MS", "60"))
    except ValueError:
        cross_ms = 60
    try:
        max_intro = int(os.getenv("STAGED_TTS_MAX_INTRO_LENGTH", "150"))
    except ValueError:
        max_intro = 150
    try:
        intro_to = max(1, int(os.getenv("STAGED_TTS_INTRO_TIMEOUT_MS", "5000")))
    except ValueError:
        intro_to = 5000
    try:
        main_to = max(1, int(os.getenv("STAGED_TTS_MAIN_TIMEOUT_MS", "30000")))
    except ValueError:
        main_to = 30000

    intro_text = text[:max_intro]
    pieces: list[tuple[np.ndarray, int]] = []
    target_sr = 22050

    # Intro (mit Timeout)
    if max_intro > 0:
        try:
            ibuf, isr = await asyncio.wait_for(
                _synth(manager, intro_engine, intro_text, voice),
                timeout=intro_to / 1000.0,
            )
            ia, isr = _to_float32_mono(ibuf, isr)
            pieces.append((ia, isr))
            target_sr = isr
            log.info("StagedTTS: Intro via %s ok (%d bytes @ %d Hz)", intro_engine, len(ibuf), isr)
        except Exception as e:
            log.warning("StagedTTS: Intro via %s failed (%s) – skipping intro", intro_engine, e)

    # Main (+ Fallback Piper) mit Timeout
    main_ok = False
    for cand in (main_engine, "piper"):
        try:
            mbuf, msr = await asyncio.wait_for(
                _synth(manager, cand, text, voice),
                timeout=main_to / 1000.0,
            )
            ma, msr = _to_float32_mono(mbuf, msr)
            if pieces:
                # ggf. resample auf target_sr
                if msr != target_sr:
                    ma = _resample_mono(ma, msr, target_sr)
                    msr = target_sr
                ma = _fade_join(pieces[-1][0], ma, target_sr, ms=cross_ms)
                pieces[-1] = (ma, target_sr)
            else:
                pieces.append((ma, msr))
                target_sr = msr
            log.info("StagedTTS: Main via %s ok (%d bytes @ %d Hz)", cand, len(mbuf), msr)
            main_ok = True
            break
        except Exception as e:
            log.warning("StagedTTS: Main via %s failed: %s", cand, e)

    if not pieces or not main_ok:
        # Harter Fallback: kompletter Text via Piper
        try:
            mbuf, msr = await asyncio.wait_for(
                _synth(manager, "piper", text, voice),
                timeout=main_to / 1000.0,
            )
            ma, msr = _to_float32_mono(mbuf, msr)
            pieces = [(ma, msr)]
            target_sr = msr
            log.info("StagedTTS: full Piper fallback ok (%d bytes @ %d Hz)", len(mbuf), msr)
        except Exception as e:
            log.error("StagedTTS: complete failure – %s", e)
            return b"", target_sr

    out = pieces[-1][0]
    return _to_int16(out).tobytes(), target_sr
