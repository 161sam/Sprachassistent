from __future__ import annotations

import io
import os
import time
import logging
from typing import Optional, Dict, Any, List

import numpy as np
import torch
import torchaudio
import soundfile as sf

# Zonos – gemäß README
# https://huggingface.co/Zyphra/Zonos-v0.1-hybrid/raw/main/README.md
from zonos.model import Zonos
from zonos.conditioning import make_cond_dict

from .base_tts_engine import (
    TTSConfig,
    TTSInitializationError,
    TTSResult,
)

logger = logging.getLogger(__name__)


class ZonosTTSEngine:
    """
    Zonos v0.1 TTS Engine
    Erwartet optional eine Sprecher-Referenzdatei in spk_cache/<voice>.* (wav/mp3/flac/m4a/ogg/webm)
    """

    def __init__(self, config: TTSConfig):
        self.config = config
        self.model: Optional[Zonos] = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._active_voice: Optional[str] = config.voice or None
        self._active_lang: str = (config.language or "de-de").lower()
        self._target_sr: int = int(config.sample_rate or 48000)

    async def initialize(self) -> bool:
        """
        Lädt das Zonos-Modell. Wir nutzen den HF-Checkpoint aus engine_params['model_id'].
        """
        try:
            model_id = (
                (self.config.engine_params or {}).get(
                    "model_id", "Zyphra/Zonos-v0.1-transformer"
                )
                or "Zyphra/Zonos-v0.1-transformer"
            )
            dtype = torch.float16 if (self.device == "cuda") else torch.float32

            logger.info(f"Zonos: lade Modell '{model_id}' auf {self.device} ({dtype}) …")
            self.model = Zonos.from_pretrained(model_id, device=self.device, dtype=dtype)  # noqa: E501
            # native Samplerate (44.1k/48k je nach Autoencoder); wir resampeln später falls nötig
            self.native_sr: int = int(getattr(self.model.autoencoder, "sampling_rate", 44100))  # noqa: E501
            logger.info(f"Zonos: initialisiert (native SR: {self.native_sr} Hz)")
            return True
        except Exception as e:
            raise TTSInitializationError(f"Zonos Init-Fehler: {e}")

    # kompatibel zur Nutzung im Manager
    async def set_voice(self, voice: Optional[str] = None, engine=None) -> bool:
        self._active_voice = voice or self._active_voice
        return True

    # --- Hilfsfunktionen --------------------------------------------------

    def _find_speaker_file(self, voice: Optional[str]) -> Optional[str]:
        if not voice:
            return None
        spk_dir = (self.config.engine_params or {}).get("speaker_dir") or os.getenv(
            "ZONOS_SPEAKER_DIR", "spk_cache"
        )
        exts = ("wav", "mp3", "flac", "m4a", "ogg", "webm")
        for ext in exts:
            cand = os.path.join(spk_dir, f"{voice}.{ext}")
            if os.path.isfile(cand):
                return cand
        return None

    def _make_speaker_embedding(self, speaker_path: str):
        wav, sr = torchaudio.load(speaker_path)  # (C, T)
        if wav.dim() == 2 and wav.size(0) > 1:
            wav = wav.mean(dim=0, keepdim=True)  # Mono
        # API aus README: model.make_speaker_embedding(wav, sampling_rate)
        return self.model.make_speaker_embedding(wav, sr)

    def _resample_if_needed(self, wav: torch.Tensor, src_sr: int) -> torch.Tensor:
        if self._target_sr and self._target_sr != src_sr:
            wav = torchaudio.functional.resample(wav, src_sr, self._target_sr)
            return wav
        return wav

    def _to_wav_bytes(self, wav: torch.Tensor, sr: int) -> bytes:
        wav_np = wav.squeeze(0).detach().cpu().numpy().astype(np.float32)
        buf = io.BytesIO()
        sf.write(buf, wav_np, sr, format="WAV", subtype="PCM_16")
        return buf.getvalue()

    # --- Synthese ---------------------------------------------------------

    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: Optional[float] = None,
        volume: Optional[float] = None,
        language: Optional[str] = None,
        **kwargs: Any,
    ) -> TTSResult:
        t0 = time.perf_counter()
        if not self.model:
            return TTSResult(False, None, 0.0, "Zonos nicht initialisiert")

        try:
            voice = voice or self._active_voice
            lang = (language or self._active_lang or "de-de").lower()

            speaker_embed = None
            spk_file = self._find_speaker_file(voice)
            if spk_file:
                try:
                    speaker_embed = self._make_speaker_embedding(spk_file)
                    logger.debug(f"Zonos: Speaker-Embedding aus {spk_file} geladen")
                except Exception as e:
                    logger.warning(f"Zonos: Speaker-Embedding fehlgeschlagen ({e}); fahre ohne fort")  # noqa: E501

            # Conditioning gemäß README
            cond_dict = make_cond_dict(text=text, language=lang, speaker=speaker_embed)
            conditioning = self.model.prepare_conditioning(cond_dict)

            # Optional rudimentäre Prosodie-Controls (speed) via conditioning-Keys:
            # Zonos unterstützt u.a. 'rate', 'pitch', 'emotion' – nur setzen falls gegeben.
            if speed is not None:
                try:
                    conditioning["rate"] = float(speed)
                except Exception:
                    pass

            codes = self.model.generate(conditioning)
            wavs: torch.Tensor = self.model.autoencoder.decode(codes).cpu()  # (B, 1, T)
            wav: torch.Tensor = wavs[0]  # (1, T)

            # Resample falls Ziel-SR gesetzt
            out_wav = self._resample_if_needed(wav, self.native_sr)
            out_sr = self._target_sr or self.native_sr

            audio_bytes = self._to_wav_bytes(out_wav, out_sr)
            dt = (time.perf_counter() - t0) * 1000.0
            return TTSResult(True, audio_bytes, dt, None)

        except Exception as e:
            dt = (time.perf_counter() - t0) * 1000.0
            return TTSResult(False, None, dt, f"Zonos Synthese-Fehler: {e}")
