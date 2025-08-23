"""Unified Piper TTS engine used by the websocket server.

This implementation exposes a minimal async API that returns a dict with
audio data and metadata so that downstream components can rely on a single
representation.  The engine reads the sample rate from the accompanying
model JSON file and always returns proper WAV bytes.
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, Optional

try:  # pragma: no cover - optional dependency is monkeypatched in tests
    from piper import PiperVoice, SynthesisConfig  # type: ignore
    _PIPER_AVAILABLE = True
except Exception as e:  # pragma: no cover - handled gracefully in __init__
    _PIPER_AVAILABLE = False
    _PIPER_IMPORT_ERROR = e

from backend.tts.base_tts_engine import BaseTTSEngine, TTSConfig, TTSInitializationError

try:
    from ws_server.tts.text_sanitizer import pre_clean_for_piper
except Exception:  # pragma: no cover - fallback for tests
    def pre_clean_for_piper(text: str) -> str:  # type: ignore
        return text

logger = logging.getLogger(__name__)


class PiperTTSEngine(BaseTTSEngine):
    """Piper wrapper that always yields WAV bytes and propagates sample rate."""

    def __init__(self, config: TTSConfig):
        if not _PIPER_AVAILABLE:  # pragma: no cover - exercised in tests
            raise ImportError(f"piper not available: {_PIPER_IMPORT_ERROR}")
        super().__init__(config)
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="PiperTTS")
        self.voice_cache: Dict[str, PiperVoice] = {}
        self.sample_rate: int = 0

        self.supported_voices = [
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

    # ------------------------------------------------------------------ helpers
    def _normalize_voice(self, voice: str) -> str:
        return (voice or "").replace("de_DE-", "de-")

    def supports_voice(self, voice: str) -> bool:  # type: ignore[override]
        return self._normalize_voice(voice) in self.supported_voices

    def _resolve_model_path(self, voice: str) -> str:
        if self.config.model_path and os.path.exists(self.config.model_path):
            return self.config.model_path

        model_filename = self.voice_model_mapping.get(self._normalize_voice(voice), f"{voice}.onnx")
        base_from_env = os.getenv("TTS_MODEL_DIR") or os.getenv("MODELS_DIR") or "models"
        project_root = Path(__file__).resolve().parents[2]
        base_abs = Path(base_from_env) if os.path.isabs(base_from_env) else project_root / base_from_env
        base_abs = base_abs.resolve()

        candidates = [
            base_abs / "piper" / model_filename,
            Path.home() / ".local/share/piper" / model_filename,
            Path("/usr/share/piper") / model_filename,
            Path(model_filename),
        ]
        for path in candidates:
            if path.exists():
                return str(path)

        fallback = Path.home() / ".local/share/piper/de-thorsten-low.onnx"
        if fallback.exists():
            logger.warning("Verwende Fallback-Modell: %s", fallback)
            return str(fallback)

        raise TTSInitializationError(f"Kein Piper-Modell gefunden (voice='{voice}')")

    def _read_sample_rate(self, model_path: str) -> int:
        json_path = Path(model_path).with_suffix(Path(model_path).suffix + ".json")
        try:
            data = json.loads(json_path.read_text())
            sr = int(data.get("sample_rate", 0))
            if sr > 0:
                return sr
        except Exception:
            pass
        if "de_DE-thorsten-low" in model_path:
            logger.warning("piper: sample_rate missing – fallback 22050 Hz")
            return 22050
        raise TTSInitializationError(f"piper: sample_rate missing for model {model_path}")

    # ---------------------------------------------------------------- info API
    def get_available_voices(self) -> list[str]:  # type: ignore[override]
        return self.supported_voices.copy()

    def get_engine_info(self) -> Dict[str, Any]:  # type: ignore[override]
        return {
            "name": "Piper TTS",
            "version": "1.0",
            "sample_rate": self.sample_rate,
            "current_voice": self.config.voice,
        }

    # ---------------------------------------------------------------- lifecycle
    async def initialize(self) -> bool:
        try:
            model_path = self._resolve_model_path(self.config.voice or "de-thorsten-low")
            self.sample_rate = self._read_sample_rate(model_path)
            loop = asyncio.get_event_loop()
            voice_obj = await loop.run_in_executor(self.executor, PiperVoice.load, model_path)
            self.voice_cache[self.config.voice or "de-thorsten-low"] = voice_obj
            self.config.model_path = model_path
            self.is_initialized = True
            logger.info("Piper init: voice=%s sr=%d", self.config.voice or "de-thorsten-low", self.sample_rate)
            return True
        except Exception as e:  # pragma: no cover - logging only
            logger.error("Piper TTS Initialisierung fehlgeschlagen: %s", e)
            self.is_initialized = False
            return False

    async def cleanup(self):
        try:
            self.executor.shutdown(wait=True)
        finally:
            self.voice_cache.clear()

    # ----------------------------------------------------------------- synthesis
    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        cfg: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Synthesize text and return wav bytes with metadata."""
        text = pre_clean_for_piper(text)
        ok, err = self.validate_text(text)
        if not ok:
            return {
                "wav_bytes": None,
                "sample_rate": self.sample_rate,
                "num_channels": 1,
                "sample_width": 2,
                "format": "wav",
                "error": err,
            }

        if not self.is_initialized:
            await self.initialize()

        target_voice = self._normalize_voice(voice or self.config.voice or "de-thorsten-low")
        try:
            wav = await self._synthesize_with_piper(text, target_voice, model_path=cfg.get("model_path") if cfg else None, **(cfg or {}))
            length_ms = int(len(wav) / (self.sample_rate * 2) * 1000) if self.sample_rate else 0
            logger.info("Piper intro: len=%s sr=%d", length_ms, self.sample_rate)
            return {
                "wav_bytes": wav,
                "sample_rate": self.sample_rate,
                "num_channels": 1,
                "sample_width": 2,
                "format": "wav",
            }
        except Exception as e:  # pragma: no cover - logging only
            logger.error("Piper TTS Synthese fehlgeschlagen: %s", e)
            return {
                "wav_bytes": None,
                "sample_rate": self.sample_rate,
                "num_channels": 1,
                "sample_width": 2,
                "format": "wav",
                "error": str(e),
            }

    async def _synthesize_with_piper(
        self,
        text: str,
        voice: str,
        model_path: Optional[str] = None,
        **options: Any,
    ) -> bytes:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, self._piper_synthesis_sync, text, voice, options, model_path
        )

    def _piper_synthesis_sync(
        self,
        text: str,
        voice: str,
        options: Dict[str, Any],
        model_path: Optional[str] = None,
    ) -> bytes:
        voice_obj = None if model_path else self.voice_cache.get(voice)
        if voice_obj is None:
            mp = model_path or self._resolve_model_path(voice)
            voice_obj = PiperVoice.load(mp)
            if model_path is None:
                self.voice_cache[voice] = voice_obj

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
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            for chunk in voice_obj.synthesize(text, syn_config=syn_cfg):
                wf.writeframes(chunk.audio_int16_bytes)
        return buf.getvalue()


__all__ = ["PiperTTSEngine"]

