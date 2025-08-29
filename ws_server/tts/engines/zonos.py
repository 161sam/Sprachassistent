# -*- coding: utf-8 -*-
"""
Zonos TTS Engine – Direct Python Import
- Lädt Zonos aus der aktiven Umgebung ODER aus ./externals/Zonos (sys.path-Fallback)
- Erstellt einmalig ein Speaker-Embedding aus $ZONOS_SPEAKER_SAMPLE (oder assets/exampleaudio.mp3)
- Asynchrones synthesize(text, voice) -> (bytes, sample_rate)
"""

from __future__ import annotations
import os, sys, asyncio, logging, time
from pathlib import Path
from typing import Optional, Tuple, Dict

log = logging.getLogger(__name__)
# Quiet-Mode: tqdm unterdrücken, wenn gewünscht
if os.getenv("ZONOS_QUIET","0").lower() in ("1","true","yes","on"):
    os.environ.setdefault("TQDM_DISABLE","1")

# --- sys.path Fallback auf externals/Zonos ---
def _ensure_zonos_on_path():
    here = Path(__file__).resolve().parents[3]  # …/Sprachassistent/ws_server/tts/engines -> 3x up -> repo root
    cand = here / "externals" / "Zonos"
    if cand.exists():
        zsrc = cand / "zonos"
        if zsrc.exists():
            p = str(cand)
            if p not in sys.path:
                sys.path.insert(0, p)
                log.debug("Zonos: added to sys.path: %s", p)

try:
    import zonos  # type: ignore
except Exception:
    _ensure_zonos_on_path()
    try:
        import zonos  # type: ignore
    except Exception as e:
        zonos = None
        _IMPORT_ERR = e
    else:
        _IMPORT_ERR = None
else:
    _IMPORT_ERR = None

# Optional: torch/torchaudio sind Zonos-Deps
try:
    import torch, torchaudio  # type: ignore
except Exception as e:
    _TORCH_ERR = e
else:
    _TORCH_ERR = None

# Lazy Singletons
_MODEL = None
_SPEAKER = None  # default speaker embedding
_SR = None
_LOCK = asyncio.Lock()
_SPEAKER_CACHE: Dict[str, object] = {}

def _pick_language(voice: Optional[str]) -> str:
    # Priorität: explicit TTS language (BCP47) > Zonos ENV > Voice-Heuristik > Default
    lang = (os.getenv("TTS_LANGUAGE") or os.getenv("ZONOS_LANGUAGE") or os.getenv("ZONOS_LANG") or "").strip().lower()
    if not lang and voice:
        v = (voice or "").lower()
        if "de" in v: lang = "de"           # de, de-de, de_thorsten_low etc.
        elif "en" in v: lang = "en-us"
        elif "fr" in v: lang = "fr-fr"
        elif "ja" in v: lang = "ja"
        elif "zh" in v or "cn" in v: lang = "zh"
    if not lang:
        lang = "de"  # Default
    return lang

def _pick_model_id() -> str:
    # akzeptiere mehrere ENV-Varianten
    return (
        os.getenv("ZONOS_MODEL_ID")
        or os.getenv("ZONOS_MODEL")
        or os.getenv("ZONOS_MODEL_NAME")
        or "Zyphra/Zonos-v0.1-transformer"
    )

def _pick_local_model_dir(repo_root: Path) -> Optional[Path]:
    """Optionaler lokaler Gewichtsordner mit config.json + model.safetensors.

    Reihenfolge:
      1) ENV (ZONOS_LOCAL_DIR / ZONOS_LOCAL_MODEL_DIR)
      2) repo_root/models/zonos/**
      3) None → verwende from_pretrained(model_id)
    """
    # 1) explicit env hints
    for key in ("ZONOS_LOCAL_DIR", "ZONOS_LOCAL_MODEL_DIR"):
        val = os.getenv(key)
        if not val:
            continue
        p = Path(val).expanduser()
        if not p.is_absolute():
            p = (repo_root / p).resolve()
        if (p / "config.json").exists() and (p / "model.safetensors").exists():
            return p
    # 2) models/zonos scan
    try:
        models_dir = (repo_root / "models" / "zonos").resolve()
        if models_dir.exists():
            # search immediate children and one level below for config+model
            cands = list(models_dir.glob("**/config.json"))
            for cfg in cands:
                base = cfg.parent
                if (base / "model.safetensors").exists():
                    return base
    except Exception:
        pass
    return None

def _pick_speaker_sample(repo_root: Path) -> Path:
    env = os.getenv("ZONOS_SPEAKER_SAMPLE")
    if env:
        p = Path(env).expanduser()
        if p.exists():
            return p
    # Fallback: mitgelieferte Probe
    cand = repo_root / "externals" / "Zonos" / "assets" / "exampleaudio.mp3"
    return cand

def _get_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]

def _speaker_cache_dir(repo_root: Path) -> Path:
    base = os.getenv("ZONOS_SPEAKER_DIR", "spk_cache")
    p = Path(base)
    if not p.is_absolute():
        p = (repo_root / p).resolve()
    return p

def _find_voice_sample(repo_root: Path, voice_id: Optional[str]) -> Optional[Path]:
    if not voice_id:
        return None
    base = _speaker_cache_dir(repo_root)
    vid = str(voice_id).strip().lower()
    # case-insensitive search for <voice_id>.<ext>
    try:
        for p in base.glob("*"):
            if not p.is_file():
                continue
            stem = p.stem.strip().lower()
            if stem == vid and p.suffix.lower() in (".wav", ".mp3", ".flac", ".ogg", ".m4a"):
                return p
    except Exception:
        pass
    return None

def _load_speaker_from_audio(path: Path):
    wav, sr = torchaudio.load(str(path))
    spk = _MODEL.make_speaker_embedding(wav, sr)
    return spk

def _get_speaker_embedding(voice_id: Optional[str]) -> object:
    """Return speaker embedding for voice_id, using cache/disk/audio, else default."""
    repo_root = _get_repo_root()
    if voice_id:
        spk = _SPEAKER_CACHE.get(voice_id)
        if spk is not None:
            return spk
        # try disk cache
        try:
            pt = _speaker_cache_dir(repo_root) / f"{voice_id}.pt"
            if pt.exists():
                import torch
                spk = torch.load(str(pt))
                _SPEAKER_CACHE[voice_id] = spk
                log.debug("Zonos: loaded speaker cache %s", pt)
                return spk
        except Exception:
            pass
        sample = _find_voice_sample(repo_root, voice_id)
        if sample and sample.exists():
            try:
                spk = _load_speaker_from_audio(sample)
                _SPEAKER_CACHE[voice_id] = spk
                # persist
                try:
                    d = _speaker_cache_dir(repo_root)
                    d.mkdir(parents=True, exist_ok=True)
                    import torch
                    torch.save(spk, str(d / f"{voice_id}.pt"))
                except Exception:
                    pass
                log.info("Zonos: speaker built from sample %s", sample)
                return spk
            except Exception as e:
                log.warning("Zonos: speaker build failed for %s: %s", sample, e)
    # no explicit sample – warn and return default speaker
    if voice_id:
        log.warning("Zonos: kein Sprecher‑Sample für '%s' gefunden – nutze Default‑Stimme", voice_id)
    return _SPEAKER

def precompute_speaker_embedding(voice_id: str) -> bool:
    """Build and persist a speaker embedding (.pt) for a given voice_id.

    Returns True on success, False otherwise. Requires that a sample file exists
    in the speaker cache directory (e.g. spk_cache/<voice_id>.wav or .mp3/.flac/.ogg/.m4a).
    """
    try:
        if not voice_id:
            return False
        # Ensure model is ready to build embeddings
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # best-effort: schedule sync wrapper
            import concurrent.futures
            fut = asyncio.run_coroutine_threadsafe(_load_once(), loop)
            fut.result(timeout=60)
        else:
            loop.run_until_complete(_load_once())
        repo_root = _get_repo_root()
        sample = _find_voice_sample(repo_root, voice_id)
        if not sample or not sample.exists():
            return False
        spk = _load_speaker_from_audio(sample)
        _SPEAKER_CACHE[voice_id] = spk
        try:
            d = _speaker_cache_dir(repo_root)
            d.mkdir(parents=True, exist_ok=True)
            import torch
            torch.save(spk, str(d / f"{voice_id}.pt"))
        except Exception:
            pass
        log.info("Zonos: precomputed speaker embedding for %s", voice_id)
        return True
    except Exception as e:
        log.warning("Zonos: precompute speaker embedding failed for %s: %s", voice_id, e)
        return False

def _np_int16_bytes(wave_tensor, sr: int) -> Tuple[bytes, int]:
    import numpy as np
    w = wave_tensor.detach().cpu().numpy()  # (B, T)
    if w.ndim == 2:
        w = w[0]
    if w.size == 0:
        return b"", sr
    # norm to int16
    m = max(1e-9, float(np.max(np.abs(w))))
    y = np.clip(w / m, -1.0, 1.0)
    y = (y * 32767.0).astype(np.int16)
    return y.tobytes(), sr

async def _load_once():
    global _MODEL, _SPEAKER, _SR
    if _MODEL is not None and _SPEAKER is not None and _SR is not None:
        return
    async with _LOCK:
        if _MODEL is not None and _SPEAKER is not None and _SR is not None:
            return

        if _IMPORT_ERR:
            raise ImportError(f"Zonos module not importable: {_IMPORT_ERR}")
        if _TORCH_ERR:
            raise ImportError(f"PyTorch/Torchaudio missing for Zonos: {_TORCH_ERR}")

        from zonos.model import Zonos as _ZonosModel  # type: ignore
        device = _pick_device()

        model_id = _pick_model_id()
        repo_root = Path(__file__).resolve().parents[3]
        local_dir = _pick_local_model_dir(repo_root)

        loop = asyncio.get_running_loop()
        log.info("Zonos: loading model %s (device=%s, local_dir=%s)…", model_id, device, local_dir)
        # Blocking load -> Thread
        def _load_model():
            if local_dir is not None:
                cfg = str(local_dir / "config.json")
                mdl = str(local_dir / "model.safetensors")
                return _ZonosModel.from_local(cfg, mdl, device=device)
            return _ZonosModel.from_pretrained(model_id, device=device)
        t0 = time.perf_counter()
        _MODEL = await loop.run_in_executor(None, _load_model)
        log.info("Zonos: model ready in %.2fs", time.perf_counter() - t0)

        # Speaker
        spk_file = _pick_speaker_sample(repo_root)
        if not spk_file.exists():
            raise FileNotFoundError(f"Speaker sample not found at {spk_file}")

        log.info("Zonos: loading speaker sample %s …", spk_file)
        def _make_speaker():
            try:
                wav, sr = torchaudio.load(str(spk_file))
            except Exception:
                # Fallback: versuche mitgelieferte WAV (kein mp3-Decoder vorhanden)
                alt = repo_root / "externals" / "Zonos" / "assets" / "silence_100ms.wav"
                wav, sr = torchaudio.load(str(alt if alt.exists() else spk_file))
            spk = _MODEL.make_speaker_embedding(wav, sr)
            return spk, _MODEL.autoencoder.sampling_rate
        t1 = time.perf_counter()
        _SPEAKER, _SR = await loop.run_in_executor(None, _make_speaker)
        log.info("Zonos ready: sr=%s (speaker in %.2fs)", _SR, time.perf_counter() - t1)

class ZonosEngine:
    """
    Leichte Zonos-Engine mit asynchroner Synthese.

    Diese Klasse implementiert eine minimal kompatible Engine-API, sodass sie
    sowohl direkt (tuple-Rückgabe) als auch über den TTSManager genutzt werden kann.
    """
    ENGINE_NAME = "zonos"

    # Manager-kompatible Felder (werden vom Manager nicht zwingend benötigt, aber hilfreich für Stats)
    is_initialized: bool = False
    config: object | None = None

    def __init__(self, *args, **kwargs):
        # akzeptiere optionale TTSConfig (z.B. vom Manager übergeben)
        self.config = kwargs.get("config") or (args[0] if args else None)

    async def initialize(self) -> bool:
        """Leichte Init: nur Import-/Umgebungsprobe, kein Modell-Download.

        Das eigentliche Laden (from_pretrained + Speaker) passiert on-demand in synthesize().
        So vermeiden wir Timeouts und Netzwerkzugriffe beim Boot.
        """
        if _IMPORT_ERR:
            log.error("Zonos Importfehler: %s", _IMPORT_ERR)
            self.is_initialized = False
            return False
        # torchaudio/torch werden erst beim ersten Syntheseaufruf benötigt
        self.is_initialized = True
        return True

    async def ensure_loaded(self) -> bool:
        """Ensure model and speaker embedding are loaded (idempotent)."""
        try:
            await _load_once()
            return True
        except Exception as e:
            log.warning("Zonos ensure_loaded fehlgeschlagen: %s", e)
            return False

    async def warmup(self, voice_id: Optional[str] = None, timeout_s: float = 2.5) -> bool:
        """Run a tiny synthesis to warm caches/graphs; returns quickly if ready."""
        try:
            await _load_once()
            async def _do():
                try:
                    txt = "ok."
                    # Use current or derived speaker id
                    vid = voice_id or None
                    await self.synthesize(txt, voice_id=vid)
                    return True
                except Exception:
                    return False
            return bool(await __import__("asyncio").wait_for(_do(), timeout=timeout_s))
        except Exception as e:
            log.debug("Zonos warmup übersprungen/fehlgeschlagen: %s", e)
            return False

    async def cleanup(self) -> None:
        """Räumt Singletons auf (freiwillig)."""
        global _MODEL, _SPEAKER, _SR
        _MODEL = None
        _SPEAKER = None
        _SR = None
        self.is_initialized = False

    def get_available_voices(self) -> list[str]:  # optional für Stats/GUI
        try:
            from ws_server.tts.voice_aliases import VOICE_ALIASES  # lazy import
            out = [k for k, m in VOICE_ALIASES.items() if m.get("zonos")]
            return sorted(set(out))
        except Exception:
            return [os.getenv("TTS_VOICE", "de-thorsten-low")]

    def get_engine_info(self) -> dict:
        return {
            "name": "Zonos",
            "version": os.getenv("ZONOS_VERSION", "0.1"),
            "sample_rate": int(_SR or 0) or 0,
            "initialized": bool(self.is_initialized),
        }

    async def synthesize(self, text: str, voice: Optional[str] = None, voice_id: Optional[str] = None, **kwargs) -> Tuple[bytes, int]:
        # Tolerate alias 'voice' and duplicate 'voice_id' in kwargs; prefer named voice_id
        if voice_id is None and "voice" in kwargs:
            try:
                voice_id = kwargs.pop("voice")
            except Exception:
                pass
        # remove any secondary voice_id to avoid multiple values
        try:
            if "voice_id" in kwargs:
                kwargs.pop("voice_id")
        except Exception:
            pass
        # Sicherstellen, dass initialisiert wurde (Manager ruft initialize() auf, aber direkter Gebrauch auch möglich)
        if not self.is_initialized:
            ok = await self.initialize()
            if not ok:
                raise RuntimeError("Zonos nicht initialisiert")

        # Sicherstellen, dass Modell & Speaker geladen sind
        await _load_once()
        lang = _pick_language(voice)
        # derive speaker id from mapping if none was passed
        if not voice_id:
            try:
                # explicit env override wins
                env_spk = os.getenv("ZONOS_SPEAKER")
                if env_spk:
                    voice_id = env_spk.strip()
                from ws_server.tts.voice_aliases import VOICE_ALIASES  # type: ignore
                vkey = (voice or os.getenv("TTS_VOICE") or "de-thorsten-low").strip()
                ev = (VOICE_ALIASES.get(vkey) or {}).get("zonos")
                if ev and getattr(ev, "voice_id", None):
                    voice_id = ev.voice_id
                else:
                    # basic derivation: 'de-thorsten-low' -> 'thorsten'
                    raw = vkey
                    mid = raw.split("-", 1)[1] if ("-" in raw) else raw
                    voice_id = mid.split("-")[0]
            except Exception:
                pass
        # Map manager/global speed to Zonos 'speaking_rate'; allow explicit env overrides.
        try:
            base_rate = float(os.getenv("ZONOS_SPEAKING_RATE", "")) if os.getenv("ZONOS_SPEAKING_RATE") else 15.0
        except Exception:
            base_rate = 15.0
        try:
            speed = kwargs.get("speed", None)
            if speed is None:
                speed = float(os.getenv("TTS_SPEED")) if os.getenv("TTS_SPEED") else None
            speed = float(speed) if speed is not None else None
        except Exception:
            speed = None
        if speed is not None:
            # speaking_rate: 30 very fast, 10 slow -> scale base by speed factor
            eff_rate = max(5.0, min(30.0, base_rate * max(0.25, min(4.0, speed))))
        else:
            eff_rate = base_rate
        try:
            pitch_std = float(os.getenv("ZONOS_PITCH_STD")) if os.getenv("ZONOS_PITCH_STD") else 0.2
        except Exception:
            pitch_std = 0.2

        # Imports hier, nachdem _load_once gesichert hat, dass zonos & torch verfügbar sind
        from zonos.conditioning import make_cond_dict  # type: ignore

        # Heavy CPU/GPU Arbeit in Thread auslagern
        loop = asyncio.get_running_loop()
        log.debug("Zonos: cond lang=%s speaking_rate=%.2f pitch_std=%s", lang, float(eff_rate), ("%.2f" % pitch_std) if pitch_std is not None else "default")

        def _generate_bytes():
            spk = _get_speaker_embedding(voice_id)
            cond = make_cond_dict(
                text=text,
                speaker=spk,
                language=lang,
                speaking_rate=float(eff_rate),
                **({"pitch_std": float(pitch_std)} if pitch_std is not None else {}),
            )
            conditioning = _MODEL.prepare_conditioning(cond)
            codes = _MODEL.generate(conditioning)
            wavs = _MODEL.autoencoder.decode(codes).cpu()
            return _np_int16_bytes(wavs, _MODEL.autoencoder.sampling_rate)
        try:
            to_ms = int(os.getenv("ZONOS_TIMEOUT_MS","30000"))
            t0 = time.perf_counter()
            audio_bytes, sr = await asyncio.wait_for(
                loop.run_in_executor(None, _generate_bytes),
                timeout=max(0.001, to_ms/1000)
            )
            log.debug("Zonos: synth len=%d sr=%d in %.2fs", len(audio_bytes or b""), int(sr or _SR or 0), time.perf_counter() - t0)
            return audio_bytes, int(sr or _SR or 22050)
        except Exception as e:
            # Provide a concise status line for diagnostics
            try:
                status = f"model={'ok' if _MODEL else 'none'} speaker={'ok' if _SPEAKER is not None else 'none'}"
            except Exception:
                status = "status=unknown"
            log.error("Zonos synth failed: %s (%s)", e, status)
            # Lass Staged-TTS fallbacken (Piper übernimmt den Main-Part)
            raise

# Backcompat alias expected by some managers
ZonosTTSEngine = ZonosEngine

def zonos_status() -> str:
    """Return a short one-line internal status string for diagnostics."""
    try:
        return f"model={'ok' if _MODEL else 'none'} speaker={'ok' if _SPEAKER is not None else 'none'} sr={int(_SR or 0)}"
    except Exception:
        return "status=unknown"
def _pick_device() -> str:
    # Env override wins; default to CPU to avoid CUDA/cuDNN issues on headless systems
    dev = (os.getenv("ZONOS_DEVICE") or "").strip().lower()
    if dev in ("cpu","cuda","cuda:0"):  # allow explicit
        return dev
    try:
        import torch
        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"
