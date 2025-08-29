"""Unified Piper TTS engine used by the websocket server.

This implementation exposes a minimal async API that returns a dict with
audio data and metadata so that downstream components can rely on a single
representation.  The engine reads the sample rate from the accompanying
model JSON file and always returns proper WAV bytes.
"""

# TODO: relocate to backend/tts to keep all engines in one place
#       (see TODO-Index.md: Backend/TTS Engines)


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

from ws_server.tts.base_tts_engine import (
    BaseTTSEngine,
    TTSConfig,
    TTSInitializationError,
)
from ws_server.tts.voice_aliases import VOICE_ALIASES
from ws_server.tts.voice_utils import canonicalize_voice

try:
    from ws_server.tts.text_sanitizer import pre_clean_for_piper
except Exception:  # pragma: no cover - fallback for tests
    def pre_clean_for_piper(text: str) -> str:  # type: ignore
        return text

logger = logging.getLogger(__name__)


def resolve_piper_model(voice: str | None, models_dir: Path) -> tuple[str, Path, int]:
    """
    Gibt (voice_canonical, model_path, sr) zurück.

    - Wenn `voice` None oder 'default': Wähle bevorzugt ein vorhandenes deutsches Modell:
      Reihenfolge: de-thorsten-low.onnx > de-thorsten-high.onnx > erstes de-*.onnx > erstes *.onnx
    - Prüfe Existenz der Datei. Wenn nicht vorhanden: suche im Verzeichnis rekursiv.
    - Ermittele SR aus JSON‑Sidecar ("*.onnx.json"). Für bekannte Thorsten‑Modelle Fallback 22050 Hz.
    - Kla re Logs (INFO): gewählte Stimme, gefundener Pfad, sr.
    - Raise ValueError, wenn nichts gefunden.
    """
    base = Path(models_dir).expanduser()
    if not base.is_absolute():
        # relative zu Repo‑Root interpretieren
        base = Path(__file__).resolve().parents[2] / base
    base = base.resolve()

    def _sr_from_sidecar(p: Path) -> int:
        try:
            js1 = p.with_suffix(p.suffix + ".json")  # model.onnx.json
            js2 = p.with_suffix(".json")  # model.json (falls vorhanden)
            for js in (js1, js2):
                if js.exists():
                    data = json.loads(js.read_text(encoding="utf-8"))
                    sr = int(data.get("sample_rate", 0) or 0)
                    if sr > 0:
                        return sr
        except Exception as e:
            logger.debug("Piper: Sidecar JSON konnte nicht gelesen werden (%s): %s", p, e)
        # Bekannte Thorsten‑Modelle -> 22050 Hz
        stem = p.stem.lower()
        if "thorsten" in stem:
            return 22050
        # Letzter Fallback
        return 22050

    def _first(patterns: list[str]) -> Path | None:
        for pat in patterns:
            for cand in base.glob(pat):
                if cand.is_file() and cand.suffix.lower() == ".onnx":
                    return cand
        return None

    # Kandidatenliste je nach Voice
    canon = canonicalize_voice(voice or "")
    selected_path: Path | None = None

    if not canon or canon == "default":
        # 1) Präferenzliste
        for name in (
            "de-thorsten-low.onnx",
            "de-thorsten-high.onnx",
        ):
            p = base / name
            if p.exists():
                selected_path = p
                canon = name.replace(".onnx", "")
                break
        # 2) erstes deutsches Modell
        if selected_path is None:
            selected_path = _first(["de-*.onnx"]) or _first(["**/de-*.onnx"])  # rekursiv
            if selected_path is not None:
                canon = selected_path.stem
        # 3) beliebiges erstes .onnx
        if selected_path is None:
            selected_path = _first(["*.onnx"]) or _first(["**/*.onnx"])  # rekursiv
            if selected_path is not None:
                canon = selected_path.stem
    else:
        # Konkrete Stimme: Versuche mehrere Namensschemata
        names = [
            f"{canon}.onnx",
        ]
        # Legacy de_DE-* Namensschema akzeptieren
        try:
            parts = canon.split("-", 1)
            if len(parts) == 2 and len(parts[0]) == 2:
                names.append(f"{parts[0]}_DE-{parts[1]}.onnx")  # de_DE-*
                names.append(f"{parts[0]}-DE-{parts[1]}.onnx")  # de-DE-*
                names.append(f"{parts[0].upper()}_DE-{parts[1]}.onnx")
        except Exception:
            pass
        for name in names:
            p = base / name
            if p.exists():
                selected_path = p
                break
        # rekursiv suchen, falls nicht direkt gefunden
        if selected_path is None:
            for name in names:
                found = list(base.glob(f"**/{name}"))
                if found:
                    selected_path = found[0]
                    break

    if selected_path is None:
        raise ValueError(
            f"Kein Piper‑Modell gefunden für Stimme '{voice or 'default'}' in {base}. "
            "Hinweis: Lege Modelle in 'models/piper/' ab oder setze PIPER_MODELS_DIR."
        )

    sr = _sr_from_sidecar(selected_path)
    logger.info(
        "Piper: Stimme='%s' → Modell='%s' (sr=%d)", canon, selected_path, sr
    )
    return canon, selected_path.resolve(), int(sr)


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
            self.config.voice = canonicalize_voice(self.config.voice)

    # ------------------------------------------------------------------ helpers
    def _normalize_voice(self, voice: str) -> str:
        return canonicalize_voice(voice or "")

    def supports_voice(self, voice: str) -> bool:  # type: ignore[override]
        return canonicalize_voice(voice) in self.supported_voices

    def _resolve_model_path(self, voice: str) -> str:
        # Nutze immer das robuste Resolver‑Verfahren, keine 'default.onnx' Annahmen.
        voice = canonicalize_voice(voice)
        # Direkt gesetzter, existenter model_path bleibt gültig
        if self.config.model_path:
            p = Path(self.config.model_path)
            if p.exists():
                return str(p.resolve())
        # Modelle‑Verzeichnis aus ENV oder Config
        models_dir = os.getenv("PIPER_MODELS_DIR") or self.config.model_dir or "models/piper"
        try:
            _vc, _mp, _sr = resolve_piper_model(voice, Path(models_dir))
            # Sample‑Rate im Objekt hinterlegen
            if not self.sample_rate:
                self.sample_rate = int(_sr)
            return str(_mp)
        except Exception as e:
            raise TTSInitializationError(str(e))

    def _read_sample_rate(self, model_path: str) -> int:
        # Delegiere an Resolver‑Logik, die Sidecar JSON oder Thorsten‑Fallback nutzt
        try:
            _ = Path(model_path)
        except Exception:
            raise TTSInitializationError(f"piper: ungültiger Modellpfad {model_path}")
        # Versuch Sidecar zu lesen (wie in resolve_piper_model)
        try:
            js1 = Path(model_path).with_suffix(Path(model_path).suffix + ".json")
            js2 = Path(model_path).with_suffix(".json")
            for js in (js1, js2):
                if js.exists():
                    data = json.loads(js.read_text(encoding="utf-8"))
                    sr = int(data.get("sample_rate", 0) or 0)
                    if sr > 0:
                        return sr
        except Exception as e:
            logger.debug("piper: sample_rate Sidecar konnte nicht gelesen werden (%s)", e)
        # Thorsten‑Heuristik
        if "thorsten" in Path(model_path).stem.lower():
            logger.info("piper: sample_rate unbekannt – setze 22050 Hz für Thorsten‑Modell")
            return 22050
        raise TTSInitializationError(f"piper: sample_rate fehlt für Modell {model_path}")

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
            # Modelle‑Verzeichnis und Default‑Voice ermitteln
            models_dir_env = os.getenv("PIPER_MODELS_DIR") or self.config.model_dir or "models/piper"
            default_voice = os.getenv("PIPER_DEFAULT_VOICE", "de-thorsten-low")
            v, mp, sr = resolve_piper_model(self.config.voice or default_voice, Path(models_dir_env))
            model_path = str(mp)
            self.sample_rate = int(sr)
            loop = asyncio.get_event_loop()
            voice_obj = await loop.run_in_executor(self.executor, PiperVoice.load, model_path)
            self.voice_cache[self.config.voice or v] = voice_obj
            self.config.model_path = model_path
            self.is_initialized = True
            logger.info(
                "Piper Initialisiert: Stimme='%s' Modell='%s' sr=%d",
                self.config.voice or v,
                Path(model_path).name,
                int(self.sample_rate),
            )
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

        # Prefer calmer, less "spiky" defaults; allow env overrides
        try:
            noise_scale = float(os.getenv("PIPER_NOISE_SCALE", "0.45"))
        except Exception:
            noise_scale = 0.45
        try:
            noise_w = float(os.getenv("PIPER_NOISE_W", "0.5"))
        except Exception:
            noise_w = 0.5
        try:
            syn_cfg = SynthesisConfig(length_scale=1.0 / speed, volume=volume, noise_scale=noise_scale, noise_w=noise_w)
        except TypeError:
            # older piper versions may not accept noise_* params
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
