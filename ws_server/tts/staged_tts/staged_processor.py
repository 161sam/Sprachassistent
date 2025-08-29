"""Deprecated wrapper for staged TTS.

Diese Datei ist veraltet. Die Staged‑TTS‑Logik wurde in
``ws_server.tts.staged_tts.adapter`` konsolidiert. Wir behalten minimale
Kompatibilität für bestehende Imports und Tests bei und delegieren alle
Aufrufe. Ein Deprecation‑Hinweis wird genau einmal pro Prozess ausgegeben.
"""

from __future__ import annotations

import base64
import io
import logging
import os
import wave
import warnings
from dataclasses import dataclass
from typing import List, Optional

log = logging.getLogger(__name__)

_DEPRECATION_EMITTED = False


def _deprecated_notice() -> None:
    global _DEPRECATION_EMITTED
    if not _DEPRECATION_EMITTED:
        warnings.warn(
            "StagedTTSProcessor ist veraltet – benutze adapter.synthesize_staged",
            DeprecationWarning,
            stacklevel=2,
        )
        log.warning("[DEPRECATED] StagedTTSProcessor – delegiere an adapter.synthesize_staged")
        _DEPRECATION_EMITTED = True


@dataclass
class TTSChunk:
    sequence_id: str
    index: int
    total: int
    engine: str
    text: str
    wav_bytes: bytes
    success: bool
    sample_rate: int


def create_chunk_message(chunk: TTSChunk) -> dict:
    """Erzeuge ein JSON‑Chunk für den Frontend‑Player (f32 + Metadaten).

    Erwartet WAV‑Bytes (mono, 16‑bit). Konvertiert Frames nach float32
    und liefert base64‑String. Crossfade‑Dauer wird aus ENV gelesen.
    """
    try:
        with wave.open(io.BytesIO(chunk.wav_bytes), "rb") as wf:
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            fr = wf.getframerate()
            frames = wf.readframes(wf.getnframes())
        if n_channels != 1 or sampwidth != 2:
            # Einfacher Downmix‑/Konvertierungs‑Guard: nur 16‑bit mono erwartet
            log.warning("staged_chunk: WAV nicht mono/16‑bit – sende Rohdaten")
            f32 = frames  # Fallback
        else:
            import numpy as np

            i16 = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
            f32 = (i16 / 32768.0).astype(np.float32).tobytes()
        b64 = base64.b64encode(f32).decode("ascii")
    except Exception:
        # Fallback: sende Originalbytes (selten, nur bei kaputten WAVs)
        b64 = base64.b64encode(chunk.wav_bytes).decode("ascii")
        fr = chunk.sample_rate or 22050

    try:
        xfade = int(os.getenv("STAGED_TTS_CROSSFADE_MS", "100") or 100)
    except Exception:
        xfade = 100
    return {
        "op": "staged_tts_chunk",
        "engine": chunk.engine,
        "index": int(chunk.index),
        "total": int(chunk.total),
        "text": chunk.text,
        "sampleRate": int(fr or chunk.sample_rate or 22050),
        "format": "f32",
        "pcm": b64,
        "crossfade_ms": xfade,
    }


@dataclass
class StagedPlan:
    intro_engine: Optional[str]
    main_engine: Optional[str]
    fast_start: bool = True


class StagedTTSProcessor:
    """Veraltete Hülle – delegiert an adapter.synthesize_staged."""

    def __init__(self, manager):
        self.mgr = manager

    async def process_staged_tts(self, text: str, voice: str) -> List[object]:
        _deprecated_notice()
        try:
            from .adapter import synthesize_staged
        except Exception as e:  # pragma: no cover - defensive
            log.error("Adapter Importfehler: %s", e)
            return []

        pcm, sr = await synthesize_staged(self.mgr, text=text, voice=voice)
        if not pcm:
            return []
        # Verpacke als ein einzelnes Chunk
        chunk = TTSChunk(
            sequence_id="staged",
            index=0,
            total=1,
            engine="staged",
            text=text,
            wav_bytes=pcm,
            success=True,
            sample_rate=sr or 22050,
        )
        return [chunk]


__all__ = ["StagedTTSProcessor", "StagedPlan", "TTSChunk", "create_chunk_message"]
