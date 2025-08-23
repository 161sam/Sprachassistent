#!/usr/bin/env python3
"""
TTS Manager für Realtime-Engine-Switching
Ermöglicht dynamischen Wechsel zwischen Piper und Kokoro TTS
"""

import asyncio
import logging
import os
import audioop
from importlib import import_module
from typing import Any, Dict, List, Optional
from enum import Enum

from .base_tts_engine import BaseTTSEngine, TTSConfig, TTSResult
from ws_server.tts.voice_aliases import VOICE_ALIASES, EngineVoice
from ws_server.tts.voice_utils import canonicalize_voice
import re
try:
    from ws_server.tts.text_sanitizer import sanitize_for_tts_strict as _sanitize_for_tts_strict, pre_clean_for_piper
except Exception:
    def _sanitize_for_tts_strict(t: str) -> str:
        import unicodedata
        t = unicodedata.normalize('NFKC', t)
        t = ''.join(c for c in unicodedata.normalize('NFD', t) if unicodedata.category(c) != 'Mn')
        t = t.replace('\u00A0',' ')
        return ' '.join(t.split())
    def pre_clean_for_piper(t: str) -> str:
        return t
COMBINING_GUARD_RE = re.compile(r"[̀-ͯ]")

from ws_server.core.config import get_tts_engine_default

logger = logging.getLogger(__name__)

TTS_ENGINE = get_tts_engine_default()

ENGINE_IMPORTS: Dict[str, tuple[str, str]] = {
    "piper": ("ws_server.tts.engines.piper", "PiperTTSEngine"),
    "kokoro": ("backend.tts.kokoro_tts_engine", "KokoroTTSEngine"),
    "zonos": ("backend.tts.engine_zonos", "ZonosTTSEngine"),
}

class TTSEngineType(Enum):
    """Verfügbare TTS-Engine-Typen"""
    PIPER = "piper"
    KOKORO = "kokoro"
    ZONOS = "zonos"

class TTSManager:
    """Manager für Multi-Engine-Support."""

    def __init__(self):
        logger.info("Initialisiere TTS-Manager...")
        self.engines: Dict[str, BaseTTSEngine] = {}
        self.default_engine: Optional[str] = None
        self.config = TTSConfig()
        self.unavailable_engines: Dict[str, str] = {}
        self._loaded_classes: Dict[str, type] = {}
        logger.info(f"Geplante TTS-Engines: {list(ENGINE_IMPORTS.keys())}")

    def _load_engine_class(self, engine_name: str):
        """Lazy-Import einer Engineklasse."""
        if engine_name in self._loaded_classes:
            return self._loaded_classes[engine_name]
        module_name, class_name = ENGINE_IMPORTS.get(engine_name, (None, None))
        if not module_name:
            return None
        try:  # pragma: no cover - Fehlerfall wird getestet
            module = import_module(module_name)
            cls = getattr(module, class_name)
            self._loaded_classes[engine_name] = cls
            return cls
        except Exception as e:  # pragma: no cover
            self.unavailable_engines[engine_name] = str(e)
            logger.warning(f"{engine_name.title()} TTS Engine nicht verfügbar: {e}")
            return None
        
    async def initialize(
        self,
        piper_config: TTSConfig | None = None,
        kokoro_config: TTSConfig | None = None,
        zonos_config: TTSConfig | None = None,
        default_engine: TTSEngineType | None = None,
    ) -> bool:
        """Initialisiere TTS-Engines mit spezifischen Konfigurationen."""
        success_count = 0

        target_engine_name = default_engine.value if default_engine else TTS_ENGINE

        engine_configs: Dict[str, TTSConfig] = {}
        if piper_config:
            engine_configs["piper"] = piper_config
        if kokoro_config:
            engine_configs["kokoro"] = kokoro_config
        if zonos_config:
            engine_configs["zonos"] = zonos_config

        engine_priority: List[str] = []
        if target_engine_name in engine_configs:
            engine_priority.append(target_engine_name)
        for name in engine_configs.keys():
            if name not in engine_priority:
                engine_priority.append(name)

        for engine_name in engine_priority:
            engine_class = self._load_engine_class(engine_name)
            if engine_class is None:
                continue
            engine = engine_class(engine_configs[engine_name])
            try:
                init_result = await asyncio.wait_for(engine.initialize(), timeout=30.0)
                if init_result:
                    self.engines[engine_name] = engine
                    success_count += 1
                    logger.info(f"✅ {engine_name.title()} TTS erfolgreich initialisiert")
                    if self.default_engine is None:
                        self.default_engine = engine_name
                        logger.info(f"🎯 Standard-Engine: {engine_name}")
                else:
                    logger.warning(f"❌ {engine_name.title()} TTS Initialisierung fehlgeschlagen")
                    self.unavailable_engines[engine_name] = "init failed"
            except asyncio.TimeoutError:
                logger.error(
                    f"⏰ {engine_name.title()} TTS Initialisierung timeout (30s) - überspringe..."
                )
                self.unavailable_engines[engine_name] = "timeout"
            except Exception as e:  # pragma: no cover
                logger.error(f"❌ {engine_name.title()} TTS Fehler: {e}")
                self.unavailable_engines[engine_name] = str(e)

        if target_engine_name == "zonos" and "zonos" not in self.engines and "piper" in self.engines:
            logger.warning("Zonos Engine nicht verfügbar, fallback auf Piper")
            self.default_engine = "piper"

        if success_count > 0:
            logger.info(f"✅ TTS-Manager initialisiert mit {success_count} Engine(s)")
            return True

        logger.error("❌ Keine TTS-Engine verfügbar!")
        return False
    
    def _resolve_engine_voice(self, engine: str, canonical_voice: str) -> EngineVoice:
        mapping = VOICE_ALIASES.get(canonical_voice, {})
        ev = mapping.get(engine)
        if not ev or (not ev.voice_id and not ev.model_path):
            raise ValueError(f"Voice '{canonical_voice}' not defined for engine '{engine}'")
        return ev

    def engine_allowed_for_voice(self, engine: str, canonical_voice: str) -> bool:
        mapping = VOICE_ALIASES.get(canonical_voice, {})
        ev = mapping.get(engine)
        return bool(ev and (ev.voice_id or ev.model_path))

    def _postprocess_audio(self, audio: bytes, sample_rate: int) -> tuple[bytes, int]:
        target_sr = int(os.getenv("TTS_TARGET_SR", sample_rate) or sample_rate)
        if target_sr and sample_rate and target_sr != sample_rate:
            audio, _ = audioop.ratecv(audio, 2, 1, sample_rate, target_sr, None)
            sample_rate = target_sr
        if os.getenv("TTS_LOUDNESS_NORMALIZE", "0") == "1":
            rms = audioop.rms(audio, 2)
            if rms:
                target = 20000
                factor = min(4.0, target / rms)
                audio = audioop.mul(audio, 2, factor)
        return audio, sample_rate

    async def synthesize(self, text: str, engine: str = None, voice: str = None, **kwargs) -> TTSResult:
        """Synthesiere Text mit gewünschter Engine"""
        # Manager-level hard sanitization
        text = _sanitize_for_tts_strict(text)
        if COMBINING_GUARD_RE.search(text):
            text = COMBINING_GUARD_RE.sub('', text)
        target_engine = engine or self.default_engine
        canonical_voice = canonicalize_voice(voice or os.getenv("TTS_VOICE", "de-thorsten-low"))
        if target_engine == "piper":
            text = pre_clean_for_piper(text)

        if not target_engine or target_engine not in self.engines:
            return TTSResult(
                audio_data=None,
                success=False,
                error_message=f"Engine '{target_engine}' nicht verfügbar",
                engine_used=target_engine or "none"
            )

        try:
            ev = self._resolve_engine_voice(target_engine, canonical_voice)
            engine_obj = self.engines[target_engine]
            if hasattr(engine_obj, "speak"):
                if target_engine == "piper":
                    raw = await engine_obj.speak(
                        text, voice=canonical_voice, config={"model_path": ev.model_path, **kwargs}
                    )
                else:
                    raw = await engine_obj.speak(text, voice=ev.voice_id, config=kwargs)
            else:
                if target_engine == "piper":
                    raw = await engine_obj.synthesize(
                        text, voice=canonical_voice, cfg={"model_path": ev.model_path, **kwargs}
                    )
                else:
                    raw = await engine_obj.synthesize(text, voice_id=ev.voice_id, **kwargs)

            if isinstance(raw, dict) and "wav_bytes" in raw:
                audio = raw.get("wav_bytes")
                sr = raw.get("sample_rate", 0)
                fmt = raw.get("format", "wav")
                err = raw.get("error")
                success = audio is not None and not err
                if success:
                    audio, sr = self._postprocess_audio(audio, sr)
                return TTSResult(
                    audio_data=audio,
                    success=success,
                    error_message=err,
                    engine_used=target_engine,
                    sample_rate=sr,
                    audio_format=fmt,
                )

            result = raw  # assume TTSResult
            if result.success and result.audio_data:
                processed, sr = self._postprocess_audio(result.audio_data, result.sample_rate)
                result.audio_data = processed
                result.sample_rate = sr
            return result
        except Exception as e:
            logger.error(f"TTS-Synthese mit {target_engine} fehlgeschlagen: {e}")
            return TTSResult(
                audio_data=None,
                success=False,
                error_message=str(e),
                engine_used=target_engine
            )
    
    # Alte switch_engine Methode wurde durch async Version ersetzt
    
    # Synchrone Versionen für Kompatibilität
    def get_available_engines_sync(self) -> List[str]:
        """Gib verfügbare Engine-Namen zurück (sync)"""
        return list(self.engines.keys())
    
    def get_current_engine_name(self) -> Optional[str]:
        """Gib aktuell aktive Engine als String zurück"""
        return self.default_engine
    
    def get_engine_stats(self) -> Dict[str, Any]:
        """Gib Engine-Statistiken für Metrics API zurück"""
        stats = {
            'available_engines': list(self.engines.keys()),
            'default_engine': self.default_engine,
            'total_engines': len(self.engines),
            'engines_status': {}
        }
        
        # Status für jede Engine
        for name, engine in self.engines.items():
            try:
                engine_info = engine.get_engine_info()
                stats['engines_status'][name] = {
                    'initialized': engine.is_initialized,
                    'name': engine_info.get('name', name),
                    'version': engine_info.get('version', 'unknown')
                }
            except Exception as e:
                stats['engines_status'][name] = {
                    'initialized': False,
                    'error': str(e)
                }
                
        return stats
    
    def get_engine_info(self, engine_name: str = None) -> Dict[str, Any]:
        """Gib Engine-Informationen zurück"""
        target_engine = engine_name or self.default_engine
        
        if target_engine not in self.engines:
            return {"error": f"Engine '{target_engine}' nicht verfügbar"}
            
        return self.engines[target_engine].get_engine_info()
    
    def get_available_voices_sync(self, engine_name: str = None) -> List[str]:
        """Gib verfügbare Stimmen für Engine zurück (sync)"""
        target_engine = engine_name or self.default_engine
        
        if target_engine not in self.engines:
            return []
            
        try:
            return self.engines[target_engine].get_available_voices()
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Voices: {e}")
            return []
    
    async def switch_engine(self, engine_type: TTSEngineType) -> bool:
        """Wechsle Standard-Engine (async Version)"""
        engine_name = engine_type.value if engine_type else None
        return self.switch_engine_sync(engine_name)
    
    def switch_engine_sync(self, engine_name: str) -> bool:
        """Wechsle Standard-Engine (synchron)"""
        if engine_name not in self.engines:
            logger.warning(f"Engine '{engine_name}' nicht verfügbar")
            return False
            
        old_engine = self.default_engine
        self.default_engine = engine_name
        logger.info(f"Engine gewechselt von '{old_engine}' zu '{engine_name}'")
        return True
    
    async def set_voice(self, voice: str, engine: TTSEngineType = None) -> bool:
        """Setze Stimme für Engine"""
        target_engine_name = engine.value if engine else self.default_engine
        
        if target_engine_name not in self.engines:
            logger.warning(f"Engine '{target_engine_name}' nicht verfügbar")
            return False
            
        try:
            engine_obj = self.engines[target_engine_name]
            # Setze Voice in der Engine (falls unterstützt)
            if hasattr(engine_obj, 'set_voice'):
                return await engine_obj.set_voice(voice)
            else:
                engine_obj.config.voice = voice
                logger.info(f"Voice '{voice}' für Engine '{target_engine_name}' gesetzt")
                return True
        except Exception as e:
            logger.error(f"Fehler beim Setzen der Voice: {e}")
            return False
    
    async def test_all_engines(self, test_text: str = "Test der Sprachsynthese") -> Dict[str, TTSResult]:
        """Teste alle verfügbaren Engines"""
        results = {}
        
        for engine_name in self.engines.keys():
            try:
                logger.info(f"Teste Engine: {engine_name}")
                result = await self.synthesize(test_text, engine=engine_name)
                results[engine_name] = result
                logger.info(f"Test für {engine_name}: {'Erfolg' if result.success else 'Fehler'}")
            except Exception as e:
                logger.error(f"Test für {engine_name} fehlgeschlagen: {e}")
                results[engine_name] = TTSResult(
                    audio_data=None,
                    success=False,
                    error_message=str(e),
                    engine_used=engine_name
                )
        
        return results
    
    def get_current_engine(self) -> Optional[TTSEngineType]:
        """Gib aktuell aktive Engine als TTSEngineType zurück"""
        if not self.default_engine:
            return None
        try:
            return TTSEngineType(self.default_engine)
        except ValueError:
            return None
    
    async def get_available_engines(self) -> List[str]:
        """Gib verfügbare Engine-Namen zurück (async Version)"""
        return list(self.engines.keys())
    
    async def get_available_voices(self, engine_name: str = None) -> List[str]:
        """Gib verfügbare Stimmen für Engine zurück (async Version)"""
        target_engine = engine_name or self.default_engine
        
        if target_engine not in self.engines:
            return []
            
        try:
            engine_obj = self.engines[target_engine]
            if hasattr(engine_obj, 'get_available_voices'):
                return engine_obj.get_available_voices()
            else:
                # Fallback: Standard-Voices zurückgeben
                return ["default"]
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Voices: {e}")
            return []
    
    async def cleanup(self):
        """Cleanup aller TTS-Engines"""
        for engine_name, engine in self.engines.items():
            try:
                await engine.cleanup()
                logger.info(f"✅ {engine_name.title()} TTS cleanup abgeschlossen")
            except Exception as e:
                logger.error(f"❌ {engine_name.title()} cleanup Fehler: {e}")
        
        self.engines.clear()
        logger.info("TTS-Manager cleanup abgeschlossen")
# Dummy TTS Manager für Fallback
# TODO: replace with dedicated mock or remove if real engines are always available
#       (see TODO-Index.md: Backend/TTS Manager)
class DummyTTSManager:
    """Dummy TTS Manager wenn echte Engines nicht verfügbar"""
    
    def __init__(self):
        logger.warning("🔄 Dummy TTS Manager aktiv - keine echte Sprachsynthese")
        self.default_engine = "dummy"
        
    async def initialize(self, preferred_engine: str = None) -> bool:
        logger.info("✅ Dummy TTS initialisiert")
        return True
        
    async def synthesize(self, text: str, engine: str = None, voice: str = None, **kwargs) -> TTSResult:
        logger.warning(f"📝 Dummy TTS: '{text[:50]}...'")
        return TTSResult(
            audio_data=b"dummy_audio_data",
            success=True,
            engine_used="dummy",
            processing_time_ms=0.1
        )
        
    def get_available_engines(self) -> List[str]:
        return ["dummy"]
        
    def get_available_voices(self, engine_name: str = None) -> List[str]:
        return ["dummy_voice"]
        
    async def cleanup(self):
        logger.info("Dummy TTS cleanup")
