#!/usr/bin/env python3
"""
Piper TTS Engine (robust & cleaned)
- Findet lokale Piper-Modelle (models/piper/*.onnx)
- „Last-mile“ Sanitization: entfernt alle kombinierenden Zeichen (U+0300–U+036F),
  inkl. U+0327 (combining cedilla), bevor PiperVoice.synthesize() läuft
- Implementiert alle abstrakten Methoden der BaseTTSEngine
"""

from __future__ import annotations

import asyncio
import io
import logging
import os
import time
import unicodedata
import wave
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from piper import PiperVoice, SynthesisConfig

from .base_tts_engine import (
    BaseTTSEngine,
    TTSConfig,
    TTSInitializationError,
    TTSResult,
)

logger = logging.getLogger(__name__)


def _local_pre_clean(text: str) -> str:
    t = unicodedata.normalize("NFKC", text or "")
    t = unicodedata.normalize("NFD", t)
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
    t = t.replace("\u00A0", " ")
    t = re.sub(r"\s+", " ", t)
    return t.strip()

try:
    from ws_server.tts.text_sanitizer import pre_clean_for_piper as _pre_clean  # type: ignore
except Exception:  # pragma: no cover
    _pre_clean = _local_pre_clean


class PiperTTSEngine(BaseTTSEngine):
    """Piper TTS Engine mit robuster Eingabereinigung."""

    # ---- Setup ----------------------------------------------------------------
    def __init__(self, config: TTSConfig):
        super().__init__(config)
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="PiperTTS")
        self.voice_cache: Dict[str, PiperVoice] = {}

        # Unterstützte Stimmen (kanonisch)
        self.supported_voices: List[str] = [
            "de-thorsten-low",
            "de-thorsten-medium",
            "de-thorsten-high",
            "de-kerstin-low",
            "de-kerstin-medium",
            "de-eva_k-low",
            "de-eva_k-medium",
            "de-ramona-low",
            "de-karlsson-low",
            "en-amy-low",
        ]
        self.supported_languages = ["de", "de-DE", "en", "en-US"]

        self.voice_model_mapping: Dict[str, str] = {
            "de-thorsten-low": "de_DE-thorsten-low.onnx",
            "de-thorsten-medium": "de_DE-thorsten-medium.onnx",
            "de-thorsten-high": "de_DE-thorsten-high.onnx",
            "de-kerstin-low": "de_DE-kerstin-low.onnx",
            "de-kerstin-medium": "de_DE-kerstin-medium.onnx",
            "de-eva_k-low": "de_DE-eva_k-low.onnx",
            "de-eva_k-medium": "de_DE-eva_k-medium.onnx",
            "de-ramona-low": "de_DE-ramona-low.onnx",
            "de-karlsson-low": "de_DE-karlsson-low.onnx",
            "en-amy-low": "en_US-amy-low.onnx",
        }

        if self.config.voice:
            self.config.voice = self._normalize_voice(self.config.voice)

    # ---- Voice/Model-Auflösung ------------------------------------------------
    def _normalize_voice(self, voice: str) -> str:
        return (voice or "").replace("de_DE-", "de-")

    def supports_voice(self, voice: str) -> bool:  # type: ignore[override]
        return self._normalize_voice(voice) in self.supported_voices

    def _resolve_model_path(self, voice: str) -> str:
        # Falls explizit konfiguriert und vorhanden
        if self.config.model_path and os.path.exists(self.config.model_path):
            return self.config.model_path

        model_filename = self.voice_model_mapping.get(self._normalize_voice(voice), f"{voice}.onnx")

        base_from_env = os.getenv("TTS_MODEL_DIR") or os.getenv("MODELS_DIR") or "models"
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        base_abs = base_from_env if os.path.isabs(base_from_env) else os.path.join(project_root, base_from_env)

        candidates = [
            os.path.join(base_abs, "piper", model_filename),
            os.path.expanduser(f"~/.local/share/piper/{model_filename}"),
            f"/usr/share/piper/{model_filename}",
            model_filename,  # falls absoluter Pfad
        ]
        for path in candidates:
            if os.path.exists(path):
                return path

        fallback = os.path.expanduser("~/.local/share/piper/de-thorsten-low.onnx")
        if os.path.exists(fallback):
            logger.warning("Verwende Fallback-Modell: %s", fallback)
            return fallback

        raise TTSInitializationError(f"Kein Piper-Modell gefunden (voice='{voice}')")

    # ---- Lifecycle ------------------------------------------------------------
    async def initialize(self) -> bool:
        try:
            model_path = self._resolve_model_path(self.config.voice or "de-thorsten-low")
            loop = asyncio.get_event_loop()
            voice_obj = await loop.run_in_executor(self.executor, PiperVoice.load, model_path)
            self.voice_cache[self.config.voice or "de-thorsten-low"] = voice_obj
            # Modellpfad für spätere Prüfungen sichern
            self.config.model_path = model_path
            self.is_initialized = True
            logger.info("Piper TTS initialisiert mit Stimme: %s", self.config.voice or "de-thorsten-low")
            return True
        except Exception as e:
            logger.error("Piper TTS Initialisierung fehlgeschlagen: %s", e)
            self.is_initialized = False
            return False

    async def cleanup(self):
        try:
            self.executor.shutdown(wait=True)
        finally:
            self.voice_cache.clear()
            logger.info("Piper TTS Engine cleanup abgeschlossen")

    # ---- Info API -------------------------------------------------------------
    def get_available_voices(self) -> List[str]:
        return self.supported_voices.copy()

    def get_engine_info(self) -> Dict[str, Any]:
        return {
            "name": "Piper TTS",
            "version": "1.0",
            "supported_voices": self.supported_voices,
            "supported_languages": self.supported_languages,
            "current_voice": self.config.voice,
            "model_path": self.config.model_path,
            "is_initialized": self.is_initialized,
        }

    def set_voice(self, voice: str) -> bool:
        voice_norm = self._normalize_voice(voice)
        if not self.supports_voice(voice_norm):
            logger.error("Stimme '%s' wird nicht unterstützt", voice)
            return False
        try:
            self.config.voice = voice_norm
            self.config.model_path = self._resolve_model_path(voice_norm)
            return True
        except Exception as e:
            logger.error("Fehler beim Setzen der Stimme: %s", e)
            return False

    # ---- Synthese -------------------------------------------------------------
    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        model_path: Optional[str] = None,
        **kwargs,
    ) -> TTSResult:
        """Öffentliche API – säubert immer vorher."""
        started = time.time()

        # 1) Last-mile Sanitizer
        # Final guard before Piper: strips all combining marks
        text = _pre_clean(text)
        # 3) Validierung der (bereits gestrippten) Eingabe
        ok, err = self.validate_text(text)
        if not ok:
            return TTSResult(audio_data=None, success=False, error_message=err, engine_used="piper")

        if not self.is_initialized:
            await self.initialize()

        target_voice = self._normalize_voice(voice or self.config.voice or "de-thorsten-low")
        if not self.supports_voice(target_voice):
            logger.warning(
                "Stimme '%s' nicht unterstützt – fallback auf '%s'",
                target_voice, self.config.voice or "de-thorsten-low"
            )
            target_voice = self._normalize_voice(self.config.voice or "de-thorsten-low")

        try:
            audio, sr = await self._synthesize_with_piper(text, target_voice, model_path=model_path, **kwargs)
            return TTSResult(
                audio_data=audio,
                success=True,
                engine_used="piper",
                sample_rate=sr,
                processing_time_ms=(time.time() - started) * 1000.0,
                voice_used=target_voice,
                audio_format="wav",
            )
        except Exception as e:
            logger.error("Piper TTS Synthese fehlgeschlagen: %s", e)
            return TTSResult(audio_data=None, success=False, error_message=str(e), engine_used="piper")

    async def _synthesize_with_piper(
        self,
        text: str,
        voice: str,
        model_path: Optional[str] = None,
        **kwargs,
    ) -> tuple[Optional[bytes], int]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self._piper_synthesis_sync, text, voice, kwargs, model_path)

    # ---- Threadpool-Arbeit (zweite Schranke) ----------------------------------
    def _piper_synthesis_sync(
        self,
        text: str,
        voice: str,
        options: Dict,
        model_path: Optional[str] = None,
    ) -> tuple[Optional[bytes], int]:
        # Nochmals hart reinigen – selbst wenn Upstream etwas vergessen hat.
        # Final guard before Piper: strips all combining marks
        text = _pre_clean(text)

        # Voice laden/cachen
        voice_obj = None if model_path else self.voice_cache.get(voice)
        if voice_obj is None:
            mp = model_path or self._resolve_model_path(voice)
            voice_obj = PiperVoice.load(mp)
            if model_path is None:
                self.voice_cache[voice] = voice_obj

        # Optionen: Speed & Volume sicher parsen
        speed = options.get("speed", getattr(self.config, "speed", 1.0))
        volume = options.get("volume", getattr(self.config, "volume", 1.0))
        try:
            speed = float(speed) if float(speed) > 0 else 1.0
        except Exception:
            speed = 1.0
        try:
            volume = float(volume)
        except Exception:
            volume = 1.0

        syn_cfg = SynthesisConfig(length_scale=1.0 / speed, volume=volume)

        # WAV in Memory schreiben
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(voice_obj.config.sample_rate)
            for chunk in voice_obj.synthesize(text, syn_config=syn_cfg):
                wf.writeframes(chunk.audio_int16_bytes)

        return buf.getvalue(), voice_obj.config.sample_rate

