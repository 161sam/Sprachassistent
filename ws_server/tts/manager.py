
from __future__ import annotations
from ws_server.tts.engines import load_engine
from ws_server.tts.exceptions import EngineUnavailable
#!/usr/bin/env python3
# ruff: noqa: E402
"""
Einheitlicher TTS-Manager

- Dynamische Engine-Auswahl (Piper, Kokoro, Zonos)
- Robustes Piper-Model-Resolving
- Sanitizing + optionales Resampling/Normalisierung
- Einheitliche Rückgabe (TTSResult)
- Auto-Init in API-Methoden

Hinweis zu Staged TTS:
Die eigentliche Orchestrierung "Piper-Intro, Zonos-Main" übernimmt dein
ws_server.tts.staged_tts.* – dieser Manager stellt die Single-Synthese
bereit, die dort aufgerufen wird.
"""

import asyncio
import logging
import os
import audioop
from pathlib import Path
from importlib import import_module
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import re

from .base_tts_engine import BaseTTSEngine, TTSConfig, TTSResult
from ws_server.tts.voice_aliases import VOICE_ALIASES, EngineVoice
from ws_server.tts.voice_utils import canonicalize_voice
from ws_server.core.config import get_tts_engine_default

logger = logging.getLogger(__name__)

# --- Text-Sanitizer (robust gegen fehlende Imports) ---
try:
    from ws_server.tts.text_sanitizer import (
        sanitize_for_tts_strict as _sanitize_for_tts_strict,
        pre_clean_for_piper,
    )
except Exception:  # pragma: no cover
    def _sanitize_for_tts_strict(t: str) -> str:
        import unicodedata
        t = unicodedata.normalize("NFKC", t)
        t = "".join(
            c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn"
        )
        t = t.replace("\u00A0", " ")
        return " ".join(t.split())

    def pre_clean_for_piper(t: str) -> str:
        return t

COMBINING_GUARD_RE = re.compile(r"[̀-ͯ]")  # combining marks

# --- Default-Engine aus Konfiguration ---
TTS_ENGINE = get_tts_engine_default()  # "piper" | "kokoro" | "zonos"

# Lazy-Import Map: { engine_name: (module_path, class_name) }
ENGINE_IMPORTS: Dict[str, Tuple[str, str]] = {
    "piper": ("ws_server.tts.engines.piper", "PiperTTSEngine"),
    "kokoro": ("ws_server.tts.engines.kokoro", "KokoroTTSEngine"),
    "zonos": ("ws_server.tts.engines.zonos", "ZonosTTSEngine"),
}


class TTSEngineType(Enum):
    PIPER = "piper"
    KOKORO = "kokoro"
    ZONOS = "zonos"


class TTSManager:
    """Manager für Multi-Engine-Support (Single Source of Truth)."""

    def __init__(self) -> None:
        logger.info("Initialisiere TTS-Manager...")
        self.engines: Dict[str, BaseTTSEngine] = {}
        self.default_engine: Optional[str] = None
        self.config = TTSConfig()  # Basiskonfig (voice, speed, volume)
        self.unavailable_engines: Dict[str, str] = {}  # name -> reason
        self._loaded_classes: Dict[str, type] = {}
        logger.info("Geplante TTS-Engines: %s", list(ENGINE_IMPORTS.keys()))

    # ---------------------------
    # Initialisierung / Engines
    # ---------------------------

    def _load_engine_class(self, engine_name: str) -> Optional[type]:
        """Lazy-Import einer Engineklasse (mit sauberem Fehlerlogging)."""
        if engine_name in self._loaded_classes:
            return self._loaded_classes[engine_name]
        module_name, class_name = ENGINE_IMPORTS.get(engine_name, (None, None))
        if not module_name:
            return None
        try:
            module = import_module(module_name)
            cls = getattr(module, class_name)
            self._loaded_classes[engine_name] = cls
            return cls
        except Exception as e:  # pragma: no cover
            # Häufige Ursache: Drittmodule importieren fälschlich TTSManager -> zirkular
            self.unavailable_engines[engine_name] = str(e)
            logger.warning("%s TTS Engine nicht verfügbar: %s", engine_name.title(), e)
            return None

    async def initialize(
        self,
        piper_config: TTSConfig | None = None,
        kokoro_config: TTSConfig | None = None,
        zonos_config: TTSConfig | None = None,
        default_engine: TTSEngineType | None = None,
    ) -> bool:
        """
        Initialisiere TTS-Engines (sofern konfiguriert/verfügbar).
        Setzt `self.default_engine` auf die erste erfolgreich initialisierte Engine
        entsprechend Priorität (gewünschte default zuerst).
        """
        # Sichtbarkeit: versuche alle Engines zu importieren (loggt Warnungen bei Problemen)
        for _name in ENGINE_IMPORTS:
            self._load_engine_class(_name)

        success_count = 0

        target_engine_name = (default_engine.value if default_engine else TTS_ENGINE) or "piper"

        # Konfigs zusammenstellen
        engine_configs: Dict[str, TTSConfig] = {}

        if piper_config is None:
            piper_config = self._build_piper_config()
        if piper_config:
            engine_configs["piper"] = piper_config
        else:
            logger.info("Piper deaktiviert (kein gültiges Modell)")

        if kokoro_config:
            engine_configs["kokoro"] = kokoro_config
        if zonos_config:
            engine_configs["zonos"] = zonos_config

        # Priorität: gewünschte zuerst, dann die übrigen
        engine_priority: List[str] = []
        if target_engine_name in engine_configs:
            engine_priority.append(target_engine_name)
        for name in engine_configs.keys():
            if name not in engine_priority:
                engine_priority.append(name)

        # Engines nacheinander initialisieren
        for engine_name in engine_priority:
            engine_class = self._load_engine_class(engine_name)
            if engine_class is None:
                continue

            engine = engine_class(engine_configs[engine_name])
            try:
                init_ok = await asyncio.wait_for(engine.initialize(), timeout=30.0)
                if init_ok:
                    self.engines[engine_name] = engine
                    success_count += 1
                    logger.info("✅ %s TTS erfolgreich initialisiert", engine_name.title())
                    if self.default_engine is None:
                        self.default_engine = engine_name
                        logger.info("🎯 Standard-Engine: %s", engine_name)
                else:
                    logger.warning("❌ %s TTS Initialisierung fehlgeschlagen", engine_name.title())
                    self.unavailable_engines[engine_name] = "init failed"
            except asyncio.TimeoutError:
                logger.error("⏰ %s TTS Initialisierung timeout – überspringe...", engine_name.title())
                self.unavailable_engines[engine_name] = "timeout"
            except Exception as e:
                logger.error("❌ %s TTS Fehler: %s", engine_name.title(), e)
                self.unavailable_engines[engine_name] = str(e)

        # Wunsch/Fallback: Wenn Zonos gewünscht war, aber nicht kam -> auf Piper fallen, wenn vorhanden
        if target_engine_name == "zonos" and "zonos" not in self.engines and "piper" in self.engines:
            logger.warning("Zonos Engine nicht verfügbar, Fallback auf Piper")
            self.default_engine = "piper"

        if success_count > 0:
            logger.info("✅ TTS-Manager initialisiert mit %d Engine(s)", success_count)
            return True

        logger.error("❌ Keine TTS-Engine verfügbar!")
        return False

    # --- Robustes Piper-Model-Resolving -------------------------------------

    def _build_piper_config(self) -> TTSConfig | None:
        """Erzeuge Piper-Konfiguration nur, wenn ein Modell für die aktuelle Stimme existiert."""
        voice = canonicalize_voice(os.getenv("TTS_VOICE", self.config.voice))
        alias = VOICE_ALIASES.get(voice, {}).get("piper")
        model = alias.model_path if alias else None
        if not model:
            logger.info("Piper deaktiviert: Kein Piper-Modell für voice=%s gefunden", voice)
            return None

        model_dir = os.getenv("TTS_MODEL_DIR", self.config.model_dir) or "models/piper"
        mp = Path(model)
        base = Path(model_dir)

        # Kandidatenliste zusammenstellen
        candidates: List[Path] = []
        # 1) direkt unter model_dir
        candidates.append(base / mp if not mp.is_absolute() else mp)
        # 2) models/piper Root
        candidates.append(Path("models/piper") / mp.name)
        # 3) Home-Pfad
        candidates.append(Path.home() / ".local/share/piper" / mp.name)
        # 4) Fuzzy-Stem in models/piper
        stem = mp.stem.lower()
        try:
            for c in Path("models/piper").glob("*.onnx"):
                cs = c.stem.lower()
                if stem in cs or cs in stem:
                    candidates.append(c)
        except Exception:
            pass
        # 5) Rekursiv unter model_dir
        try:
            for c in base.glob("**/*.onnx"):
                cs = c.stem.lower()
                if stem in cs or cs in stem:
                    candidates.append(c)
        except Exception:
            pass

        # Duplikate entfernen
        uniq: List[Path] = []
        seen = set()
        for c in candidates:
            try:
                k = c.resolve()
            except Exception:
                k = c
            if k not in seen:
                seen.add(k)
                uniq.append(c)

        found = next((c for c in uniq if c.exists()), None)
        if not found:
            tried_list = [str(c) for c in uniq]
            logger.info(
                "Piper deaktiviert: Kein Piper-Modell für voice=%s gefunden (alias=%s). Tried: %s",
                voice, model, tried_list,
            )
            return None

        mp = found.resolve()
        logger.info("Piper-Modell gewählt: %s (exists=%s)", mp, mp.exists())

        return TTSConfig(
            engine_type="piper",
            model_path=str(mp),
            voice=voice,
            speed=self.config.speed or 1.0,
            volume=self.config.volume or 1.0,
            language="de",
            sample_rate=22050,
            model_dir=self.config.model_dir,
        )

    # ---------------------------
    # Voice/Engine-Helfer
    # ---------------------------

    def _resolve_engine_voice(self, engine: str, canonical_voice: str) -> EngineVoice:
        mapping = VOICE_ALIASES.get(canonical_voice, {})
        ev = mapping.get(engine)
        if not ev or (not ev.voice_id and not ev.model_path):
            raise ValueError(f"Voice '{canonical_voice}' not defined for engine '{engine}'")
        return ev

    def engine_allowed_for_voice(self, engine: str, voice: str) -> bool:
        canonical = canonicalize_voice(voice)
        mapping = VOICE_ALIASES.get(canonical) or VOICE_ALIASES.get(voice)
        if not mapping:
            return False
        ev = mapping.get(engine)
        return bool(ev and (ev.voice_id or ev.model_path))

    def get_canonical_voice(self, voice: Optional[str]) -> str:
        return canonicalize_voice(voice or os.getenv("TTS_VOICE", "de-thorsten-low"))

    # ---------------------------
    # Audio-Nachbearbeitung
    # ---------------------------

    def _postprocess_audio(self, audio: bytes, sample_rate: int) -> Tuple[bytes, int]:
        """
        Optionales Resampling & Loudness-Normalisierung (per ENV):
          - TTS_TARGET_SR: gewünschte Ausgaberate (int)
          - TTS_LOUDNESS_NORMALIZE: "1" aktiviert RMS-basierte Pegelanpassung
        """
        try:
            target_sr = int(os.getenv("TTS_TARGET_SR", "") or sample_rate)
        except Exception:
            target_sr = sample_rate

        if target_sr and sample_rate and target_sr != sample_rate:
            audio, _ = audioop.ratecv(audio, 2, 1, sample_rate, target_sr, None)
            sample_rate = target_sr

        if os.getenv("TTS_LOUDNESS_NORMALIZE", "0") == "1":
            rms = audioop.rms(audio, 2)
            if rms:
                target = 20000
                factor = min(4.0, target / max(rms, 1))
                audio = audioop.mul(audio, 2, factor)

        return audio, sample_rate

    # ---------------------------
    # Synthese-APIs
    # ---------------------------

    async def synthesize(
        self,
        text: str,
        engine: Optional[TTSEngineType | str] = None,
        voice: Optional[str] = None,
        **kwargs: Any,
    ) -> TTSResult:
        """
        Haupt-Synthese: Sanitizing, Engine-Aufruf, Ergebnis-Vereinheitlichung (TTSResult),
        Audio-Postprocessing (Resampling/Loudness).
        """
        # Auto-Init Guard
        if not self.engines:
            await self.initialize()

        if not text:
            return TTSResult(
                audio_data=None,
                success=False,
                error_message="leer",
                engine_used=(engine.value if isinstance(engine, TTSEngineType) else engine) or (self.default_engine or "none"),
            )

        # Sanitizing
        text = _sanitize_for_tts_strict(text)
        if COMBINING_GUARD_RE.search(text):
            text = COMBINING_GUARD_RE.sub("", text)

        # Ziel-Engine bestimmen
        if isinstance(engine, TTSEngineType):
            target_engine = engine.value
        elif isinstance(engine, str) and engine:
            target_engine = engine
        else:
            target_engine = self.default_engine

        canonical_voice = canonicalize_voice(voice or os.getenv("TTS_VOICE", "de-thorsten-low"))

        # Piper-Vorreinigung
        if target_engine == "piper":
            text = pre_clean_for_piper(text)

        if not target_engine or target_engine not in self.engines:
            return TTSResult(
                audio_data=None,
                success=False,
                error_message=f"Engine '{target_engine}' nicht verfügbar",
                engine_used=target_engine or "none",
            )

        try:
            ev = self._resolve_engine_voice(target_engine, canonical_voice)
            engine_obj = self.engines[target_engine]

            # Piper: gewünschten model_path in die Engine-Config legen (keine Doppelübergabe)
            if target_engine == "piper" and hasattr(engine_obj, "config"):
                try:
                    engine_obj.config.model_path = ev.model_path
                except Exception:
                    pass

            # Engine-Aufruf
            raw: Any
            if hasattr(engine_obj, "speak"):
                if target_engine == "piper":
                    raw = await engine_obj.speak(text, voice=canonical_voice, config=kwargs)
                else:
                    raw = await engine_obj.speak(text, voice=ev.voice_id, config=kwargs)
            else:
                if target_engine == "piper":
                    raw = await engine_obj.synthesize(text, voice=canonical_voice, cfg=kwargs)
                else:
                    raw = await engine_obj.synthesize(text, voice_id=ev.voice_id, **kwargs)

            # Vereinheitlichen -> TTSResult
            if isinstance(raw, dict) and "wav_bytes" in raw:
                audio: Optional[bytes] = raw.get("wav_bytes")
                sr = int(raw.get("sample_rate", 0) or 0)
                fmt = str(raw.get("format", "wav") or "wav")
                err = raw.get("error")
                success = bool(audio) and not err
                if success:
                    audio, sr = self._postprocess_audio(audio, sr)
                return TTSResult(
                    audio_data=audio,
                    success=success,
                    error_message=str(err) if err else None,
                    engine_used=target_engine,
                    sample_rate=sr,
                    audio_format=fmt,
                    voice_used=canonical_voice,
                )

            # Andernfalls: raw ist bereits ein TTSResult
            result: TTSResult = raw
            if result.success and result.audio_data:
                processed, sr = self._postprocess_audio(result.audio_data, result.sample_rate or 0)
                result.audio_data = processed
                result.sample_rate = sr
            if not getattr(result, "voice_used", None):
                result.voice_used = canonical_voice
            if not getattr(result, "engine_used", None):
                result.engine_used = target_engine
            return result

        except Exception as e:
            logger.error("TTS-Synthese mit %s fehlgeschlagen: %s", target_engine, e)
            return TTSResult(
                audio_data=None,
                success=False,
                error_message=str(e),
                engine_used=target_engine,
                voice_used=canonical_voice,
            )

    async def synthesize_text(self, text: str, voice: Optional[str] = None, **kw: Any) -> Optional[bytes]:
        """
        Kompat-Shortcut: liefert direkt WAV-Bytes (oder None). Wird z.B. vom WS-Server erwartet.
        """
        # Auto-Init Guard
        if not self.engines:
            await self.initialize()
        res = await self.synthesize(text=text, voice=voice, **kw)
        return res.audio_data if res and res.success else None

    async def speak(self, text: str, voice: Optional[str] = None, **kw: Any) -> Dict[str, Any]:
        """
        Einheitliche Speak-API im Dict-Format (nützlich für Tests/Tools).
        """
        res = await self.synthesize(text=text, voice=voice, **kw)
        return {
            "wav_bytes": getattr(res, "audio_data", None),
            "sample_rate": getattr(res, "sample_rate", 0),
            "format": getattr(res, "audio_format", "wav"),
            "error": None if getattr(res, "success", False) else getattr(res, "error_message", "unknown"),
            "engine_used": getattr(res, "engine_used", None),
            "voice_used": getattr(res, "voice_used", None),
        }

    # ---------------------------
    # Query-/Control-APIs
    # ---------------------------

    async def get_available_engines(self) -> List[str]:
        return list(self.engines.keys())

    def get_available_engines_sync(self) -> List[str]:
        return list(self.engines.keys())

    def get_current_engine(self) -> Optional[TTSEngineType]:
        if not self.default_engine:
            return None
        try:
            return TTSEngineType(self.default_engine)
        except ValueError:
            return None

    def get_current_engine_name(self) -> Optional[str]:
        return self.default_engine

    def get_engine_info(self, engine_name: Optional[str] = None) -> Dict[str, Any]:
        target = engine_name or self.default_engine
        if not target or target not in self.engines:
            return {"error": f"Engine '{target}' nicht verfügbar"}
        try:
            return self.engines[target].get_engine_info()
        except Exception as e:
            return {"error": str(e)}

    def get_engine_stats(self) -> Dict[str, Any]:
        stats = {
            "available_engines": list(self.engines.keys()),
            "default_engine": self.default_engine,
            "total_engines": len(self.engines),
            "engines_status": {},
        }
        for name, engine in self.engines.items():
            try:
                info = engine.get_engine_info()
                stats["engines_status"][name] = {
                    "initialized": getattr(engine, "is_initialized", False),
                    "name": info.get("name", name) if isinstance(info, dict) else name,
                    "version": (info.get("version") if isinstance(info, dict) else "unknown") or "unknown",
                }
            except Exception as e:
                stats["engines_status"][name] = {"initialized": False, "error": str(e)}
        return stats

    async def get_available_voices(self, engine_name: Optional[str] = None) -> List[str]:
        target = engine_name or self.default_engine
        if not target or target not in self.engines:
            return []
        try:
            eng = self.engines[target]
            return list(eng.get_available_voices()) if hasattr(eng, "get_available_voices") else ["default"]
        except Exception as e:
            logger.error("Fehler beim Abrufen der Voices: %s", e)
            return []

    def get_available_voices_sync(self, engine_name: Optional[str] = None) -> List[str]:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.get_available_voices(engine_name))

    async def switch_engine(self, engine_type: TTSEngineType) -> bool:
        return self.switch_engine_sync(engine_type.value if engine_type else None)

    def switch_engine_sync(self, engine_name: Optional[str]) -> bool:
        if not engine_name or engine_name not in self.engines:
            logger.warning("Engine '%s' nicht verfügbar", engine_name)
            return False
        old = self.default_engine
        self.default_engine = engine_name
        logger.info("Engine gewechselt von '%s' zu '%s'", old, engine_name)
        return True

    async def set_voice(self, voice: str, engine: TTSEngineType | None = None) -> bool:
        """Voice auf Engine setzen (falls Engine API bietet, sonst Config-Feld setzen)."""
        target = engine.value if engine else self.default_engine
        if not target or target not in self.engines:
            logger.warning("Engine '%s' nicht verfügbar", target)
            return False
        try:
            eng = self.engines[target]
            v = canonicalize_voice(voice)
            if hasattr(eng, "set_voice"):
                return await eng.set_voice(v)
            eng.config.voice = v
            logger.info("Voice '%s' für Engine '%s' gesetzt", v, target)
            return True
        except Exception as e:
            logger.error("Fehler beim Setzen der Voice: %s", e)
            return False

    async def test_all_engines(self, test_text: str = "Test der Sprachsynthese") -> Dict[str, TTSResult]:
        """Kurzer Selbsttest aller geladenen Engines."""
        out: Dict[str, TTSResult] = {}
        for name in list(self.engines.keys()):
            try:
                logger.info("Teste Engine: %s", name)
                res = await self.synthesize(test_text, engine=name)
                out[name] = res
                logger.info("Test für %s: %s", name, "Erfolg" if res.success else "Fehler")
            except Exception as e:
                logger.error("Test für %s fehlgeschlagen: %s", name, e)
                out[name] = TTSResult(
                    audio_data=None, success=False, error_message=str(e), engine_used=name
                )
        return out

    async def cleanup(self) -> None:
        """Engines aufräumen."""
        for name, eng in list(self.engines.items()):
            try:
                await eng.cleanup()
                logger.info("✅ %s TTS cleanup abgeschlossen", name.title())
            except Exception as e:
                logger.error("❌ %s cleanup Fehler: %s", name.title(), e)
        self.engines.clear()
        logger.info("TTS-Manager cleanup abgeschlossen")


__all__ = ["TTSManager", "TTSEngineType", "TTSConfig", "TTSResult"]



# --- STAGED_TTS::activate ---
try:
    import asyncio
    from .staged_tts.adapter import synthesize_staged
    async def _synth_staged_bridge(self, text: str, voice: str|None=None):
        audio, sr = await synthesize_staged(self, text, voice)
        return (audio, sr)
    if not hasattr(globals().get('TTSManager', None), '_staged_bridge_added'):
        TM = globals().get('TTSManager', None)
        if TM and hasattr(TM, 'synthesize'):
            orig = TM.synthesize
            async def synth(self, text: str, engine: str|None=None, voice: str|None=None, **kw):
                if engine and engine.lower()=='staged':
                    return await _synth_staged_bridge(self, text, voice)
                return await orig(self, text, engine=engine, voice=voice, **kw)
            TM.synthesize = synth
            TM._staged_bridge_added = True
except Exception as e:
    import logging as _lg; _lg.getLogger(__name__).warning('staged bridge not attached: %s', e)
