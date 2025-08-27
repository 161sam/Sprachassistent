# -*- coding: utf-8 -*-
"""
Zonos TTS Engine – Direct Python Import
- Lädt Zonos aus der aktiven Umgebung ODER aus ./externals/Zonos (sys.path-Fallback)
- Erstellt einmalig ein Speaker-Embedding aus $ZONOS_SPEAKER_SAMPLE (oder assets/exampleaudio.mp3)
- Asynchrones synthesize(text, voice) -> (bytes, sample_rate)
"""

from __future__ import annotations
import os, sys, asyncio, logging
from pathlib import Path
from typing import Optional, Tuple

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
_SPEAKER = None
_SR = None
_LOCK = asyncio.Lock()

def _pick_language(voice: Optional[str]) -> str:
    # Priorität: ENV > Voice-Heuristik > Default
    lang = (os.getenv("ZONOS_LANGUAGE") or "").strip().lower()
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
    return os.getenv("ZONOS_MODEL_NAME", "Zyphra/Zonos-v0.1-transformer")

def _pick_speaker_sample(repo_root: Path) -> Path:
    env = os.getenv("ZONOS_SPEAKER_SAMPLE")
    if env:
        p = Path(env).expanduser()
        if p.exists():
            return p
    # Fallback: mitgelieferte Probe
    cand = repo_root / "externals" / "Zonos" / "assets" / "exampleaudio.mp3"
    return cand

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
        from zonos.utils import DEFAULT_DEVICE as device  # type: ignore

        model_id = _pick_model_id()

        loop = asyncio.get_running_loop()
        log.info("Zonos: loading model %s …", model_id)
        # Blocking load -> Thread
        def _load_model():
            return _ZonosModel.from_pretrained(model_id, device=device)
        _MODEL = await loop.run_in_executor(None, _load_model)

        # Speaker
        repo_root = Path(__file__).resolve().parents[3]
        spk_file = _pick_speaker_sample(repo_root)
        if not spk_file.exists():
            raise FileNotFoundError(f"Speaker sample not found at {spk_file}")

        log.info("Zonos: loading speaker sample %s …", spk_file)
        def _make_speaker():
            wav, sr = torchaudio.load(str(spk_file))
            spk = _MODEL.make_speaker_embedding(wav, sr)
            return spk, _MODEL.autoencoder.sampling_rate
        _SPEAKER, _SR = await loop.run_in_executor(None, _make_speaker)
        log.info("Zonos ready: sr=%s", _SR)

class ZonosEngine:
    """
    Erwartete Engine-API:
      async def synthesize(self, text: str, voice: Optional[str] = None) -> Tuple[bytes, int]
    """
    ENGINE_NAME = "zonos"

    def __init__(self, *_, **__):
        # Lazy-Init – tatsächliches Laden erst bei der ersten Synthese
        pass

    async def synthesize(self, text: str, voice: Optional[str] = None) -> Tuple[bytes, int]:
        await _load_once()
        lang = _pick_language(voice)

        # Imports hier, nachdem _load_once gesichert hat, dass zonos & torch verfügbar sind
        from zonos.conditioning import make_cond_dict  # type: ignore

        # Heavy CPU/GPU Arbeit in Thread auslagern
        loop = asyncio.get_running_loop()

        def _generate_bytes():
            cond = make_cond_dict(text=text, speaker=_SPEAKER, language=lang)
            conditioning = _MODEL.prepare_conditioning(cond)
            codes = _MODEL.generate(conditioning)
            wavs = _MODEL.autoencoder.decode(codes).cpu()
            return _np_int16_bytes(wavs, _MODEL.autoencoder.sampling_rate)
        try:
            to_ms = int(os.getenv("ZONOS_TIMEOUT_MS","30000"))
            audio_bytes, sr = await asyncio.wait_for(
                loop.run_in_executor(None, _generate_bytes),
                timeout=max(0.001, to_ms/1000)
            )
            return audio_bytes, int(sr or _SR or 22050)
        except Exception as e:
            log.error("Zonos synth failed: %s", e)
            # Lass Staged-TTS fallbacken (Piper übernimmt den Main-Part)
            raise

# Backcompat alias expected by some managers
ZonosTTSEngine = ZonosEngine

