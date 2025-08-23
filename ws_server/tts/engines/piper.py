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
from typing import Any, Dict, Optional, Tuple

try:  # pragma: no cover - optional dependency is monkeypatched in tests
    from piper import PiperVoice, SynthesisConfig  # type: ignore
    _PIPER_AVAILABLE = True
except Exception as e:  # pragma: no cover - handled gracefully in __init__
    _PIPER_AVAILABLE = False
    _PIPER_IMPORT_ERROR = e

from backend.tts.base_tts_engine import (
    BaseTTSEngine,
    TTSConfig,
    TTSInitializationError,
)
from ws_server.tts.voice_aliases import VOICE_ALIASES

try:
    from ws_server.tts.text_sanitizer import pre_clean_for_piper
except Exception:  # pragma: no cover - fallback for tests
    def pre_clean_for_piper(text: str) -> str:  # type: ignore
        return text

logger = logging.getLogger(__name__)


def _read_sample_rate(model_path: Path) -> int:
    """Read sample rate from accompanying JSON metadata."""
    json_path = model_path.with_suffix(model_path.suffix + ".json")
    try:
        data = json.loads(json_path.read_text())
        sr = int(data.get("sample_rate", 0))
        if sr > 0:
            return sr
    except Exception:
        pass
    raise TTSInitializationError(
        f"piper: sample_rate missing for model {model_path}"
    )


def resolve_voice(voice: str) -> Tuple[Path, int]:
    """Resolve a voice alias to an absolute model path and sample rate."""
    normalized = voice.replace("de_DE-", "de-")
    alias = VOICE_ALIASES.get(normalized, {}).get("piper")

    model_candidates = []
    if alias and alias.model_path:
        model_candidates.append(Path(alias.model_path).name)
    model_candidates.append(f"{normalized}.onnx")
    if normalized.startswith("de-") and not normalized.startswith("de_DE-"):
        model_candidates.append(f"de_DE-{normalized[3:]}.onnx")

    base_from_env = os.getenv("TTS_MODEL_DIR") or os.getenv("MODELS_DIR") or "models"
    project_root = Path(__file__).resolve().parents[2]
    base_abs = (
        Path(base_from_env)
        if os.path.isabs(base_from_env)
        else (project_root / base_from_env)
    ).resolve()

    search_paths = []
    for name in model_candidates:
        search_paths.extend(
            [
                base_abs / name,
                base_abs / "piper" / name,
                Path.home() / ".local/share/piper" / name,
                Path("/usr/share/piper") / name,
                Path(name),
            ]
        )

    for path in search_paths:
        if path.exists():
            resolved = path.resolve()
            sr = _read_sample_rate(resolved)
            return resolved, sr

    raise TTSInitializationError(f"Kein Piper-Modell gefunden (voice='{voice}')")


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
        if self.config.voice:
            self.config.voice = self._normalize_voice(self.config.voice)

    # ------------------------------------------------------------------ helpers
    def _normalize_voice(self, voice: str) -> str:
        return (voice or "").replace("de_DE-", "de-")

    def supports_voice(self, voice: str) -> bool:  # type: ignore[override]
        return self._normalize_voice(voice) in self.supported_voices

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
            model_path, self.sample_rate = resolve_voice(self.config.voice or "de-thorsten-low")
            loop = asyncio.get_event_loop()
            voice_obj = await loop.run_in_executor(self.executor, PiperVoice.load, str(model_path))
            self.voice_cache[self.config.voice or "de-thorsten-low"] = voice_obj
            self.config.model_path = str(model_path)
            self.is_initialized = True
            logger.info(
                "Voice alias '%s' resolved to model '%s' (sr=%dHz)",
                self.config.voice or "de-thorsten-low",
                model_path.name,
                self.sample_rate,
            )
            return True
        except Exception as e:  # pragma: no cover - logging only
            logger.warning("Piper TTS Initialisierung fehlgeschlagen: %s", e)
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

    async def speak(
        self,
        text: str,
        voice: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Compatibility wrapper exposing a uniform speak API."""
        return await self.synthesize(text, voice, config)

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
        mp: Path
        if voice_obj is None:
            if model_path:
                mp = Path(model_path).resolve()
                if self.sample_rate == 0:
                    try:
                        self.sample_rate = _read_sample_rate(mp)
                    except Exception:
                        pass
            else:
                mp, sr = resolve_voice(voice)
                self.sample_rate = sr
            voice_obj = PiperVoice.load(str(mp))
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


__all__ = ["PiperTTSEngine", "resolve_voice"]

