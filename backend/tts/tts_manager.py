#!/usr/bin/env python3
"""
TTS Manager für Realtime-Engine-Switching
Ermöglicht dynamischen Wechsel zwischen Piper und Kokoro TTS
"""
from .engine_zonos import ZonosTTSEngine  # optional

import asyncio
import logging
import time
import os
from typing import Dict, Optional, List, Any, Union
from enum import Enum

from .base_tts_engine import BaseTTSEngine, TTSConfig, TTSResult, TTSEngineError
from .piper_tts_engine import PiperTTSEngine

# Optional Kokoro Import depending on environment
TTS_ENGINE = os.getenv("TTS_ENGINE", "piper").lower()
if TTS_ENGINE == "kokoro":  # noqa: F401
    from .kokoro_tts_engine import KokoroTTSEngine
else:  # pragma: no cover - optional dependency
    try:
        from .kokoro_tts_engine import KokoroTTSEngine  # type: ignore
    except Exception:  # pragma: no cover
        KokoroTTSEngine = None  # type: ignore

logger = logging.getLogger(__name__)

class TTSEngineType(Enum):
    """Verfügbare TTS-Engine-Typen"""
    PIPER = "piper"
    KOKORO = "kokoro"
    ZONOS = "zonos"

class TTSManager:
    """Manager für TTS-Engines mit Realtime-Switching"""
    
    def __init__(self):
        self.engines: Dict[TTSEngineType, BaseTTSEngine] = {}
        self.active_engine: Optional[TTSEngineType] = None
        self.default_configs: Dict[TTSEngineType, TTSConfig] = {}
        
        # Performance-Tracking
        self.engine_stats: Dict[TTSEngineType, Dict[str, Any]] = {
            TTSEngineType.PIPER: {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "total_processing_time_ms": 0.0,
                "average_processing_time_ms": 0.0,
                "last_used": None
            },
            TTSEngineType.KOKORO: {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "total_processing_time_ms": 0.0,
                "average_processing_time_ms": 0.0,
                "last_used": None
            },
            TTSEngineType.ZONOS: {   # <— neu
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "total_processing_time_ms": 0.0,
                "average_processing_time_ms": 0.0,
                "last_used": None
            }
        }
        
        # Engine-Switching-Callbacks
        self.engine_change_callbacks: List[callable] = []
        
    async def initialize(self,
                        piper_config: Optional[TTSConfig] = None,
                        kokoro_config: Optional[TTSConfig] = None,
			zonos_config: Optional[TTSConfig] = None,
                        default_engine: TTSEngineType = TTSEngineType.PIPER) -> bool:
        """
        Initialisiere TTS-Manager mit beiden Engines
        
        Args:
            piper_config: Konfiguration für Piper TTS
            kokoro_config: Konfiguration für Kokoro TTS
            default_engine: Standard-Engine beim Start
            
        Returns:
            bool: True wenn mindestens eine Engine erfolgreich initialisiert wurde
        """
        logger.info("Initialisiere TTS-Manager...")
        
        success_count = 0
        
        # Standard-Konfigurationen erstellen falls nicht gegeben
        if piper_config is None:
            piper_config = TTSConfig(
                engine_type="piper",
                model_path="",  # Wird automatisch ermittelt
                voice="de-thorsten-low",
                speed=1.0,
                language="de",
                sample_rate=22050,
                model_dir="models"
            )
            
        if kokoro_config is None:
            kokoro_config = TTSConfig(
                engine_type="kokoro",
                model_path="",  # Wird automatisch ermittelt
                voice="af_sarah",
                speed=1.0,
                language="en",  # Kokoro hat bessere englische Stimmen
                sample_rate=24000,
                model_dir="models"
            )
            
        self._validate_model_dir(piper_config)
        self._validate_model_dir(kokoro_config)

        self.default_configs[TTSEngineType.PIPER] = piper_config
        self.default_configs[TTSEngineType.KOKORO] = kokoro_config
        
        # Piper TTS initialisieren
        try:
            logger.info("Initialisiere Piper TTS Engine...")
            piper_engine = PiperTTSEngine(piper_config)
            if await piper_engine.initialize():
                self.engines[TTSEngineType.PIPER] = piper_engine
                success_count += 1
                logger.info("✅ Piper TTS erfolgreich initialisiert")
            else:
                logger.error("❌ Piper TTS Initialisierung fehlgeschlagen")
        except Exception as e:
            logger.error(f"❌ Piper TTS Fehler: {e}")
            
        # Kokoro TTS initialisieren
        try:
            logger.info("Initialisiere Kokoro TTS Engine...")
            if KokoroTTSEngine is not None:
                kokoro_engine = KokoroTTSEngine(kokoro_config)
                if await kokoro_engine.initialize():
                    self.engines[TTSEngineType.KOKORO] = kokoro_engine
                    success_count += 1
                    logger.info("✅ Kokoro TTS erfolgreich initialisiert")
                else:
                    logger.error("❌ Kokoro TTS Initialisierung fehlgeschlagen")
            else:
                logger.warning("KokoroTTSEngine nicht verfügbar")
        except Exception as e:
            logger.error(f"❌ Kokoro TTS Fehler: {e}")
            
        # Defaults anlegen
        if zonos_config is None:
            zonos_config = TTSConfig(
                engine_type="zonos",
                model_path="",  # wird via model_id aus engine_params gesteuert
                voice=os.getenv("ZONOS_VOICE", "thorsten"),
                speed=float(os.getenv("TTS_SPEED", "1.0")),
                language=os.getenv("ZONOS_LANG", "de-de"),
                sample_rate=int(os.getenv("TTS_OUTPUT_SR", "48000")),
                model_dir=os.getenv("TTS_MODEL_DIR", "models"),
                engine_params={
                    "model_id": os.getenv("ZONOS_MODEL", "Zyphra/Zonos-v0.1-transformer"),
                    "lang": os.getenv("ZONOS_LANG", "de-de"),
                    "output_sr": int(os.getenv("TTS_OUTPUT_SR", "48000")),
                    "speaker_dir": os.getenv("ZONOS_SPEAKER_DIR", "spk_cache"),
                }
            )

        self._validate_model_dir(zonos_config)  # harmless, legt nur Verzeichnis an

        self.default_configs[TTSEngineType.ZONOS] = zonos_config

        # Zonos initialisieren
        try:
            logger.info("Initialisiere Zonos TTS Engine...")
            zonos_engine = ZonosTTSEngine(zonos_config)
            if await zonos_engine.initialize():
                self.engines[TTSEngineType.ZONOS] = zonos_engine
                success_count += 1
                logger.info("✅ Zonos TTS erfolgreich initialisiert")
            else:
                logger.error("❌ Zonos TTS Initialisierung fehlgeschlagen")
        except Exception as e:
            logger.error(f"❌ Zonos TTS Fehler: {e}")

        # Standard-Engine setzen
        if default_engine in self.engines:
            self.active_engine = default_engine
        elif self.engines:
            # Erste verfügbare Engine als Standard
            self.active_engine = next(iter(self.engines.keys()))
        else:
            logger.error("❌ Keine TTS-Engine verfügbar!")
            return False
            
        logger.info(f"🎯 Standard-Engine: {self.active_engine.value}")
        logger.info(f"✅ TTS-Manager initialisiert mit {success_count} Engine(s)")
        
        return success_count > 0

    def _validate_model_dir(self, config: TTSConfig) -> None:
        """Stelle sicher, dass das Modellverzeichnis existiert und lesbar ist."""
        if not config.model_dir:
            config.model_dir = "models"
        try:
            os.makedirs(config.model_dir, exist_ok=True)
        except Exception as err:
            logger.error(f"Kann Modell-Verzeichnis '{config.model_dir}' nicht anlegen: {err}")
        if not os.access(config.model_dir, os.R_OK):
            logger.warning(f"Modell-Verzeichnis '{config.model_dir}' ist nicht lesbar")
        
    async def synthesize(self, 
                        text: str, 
                        engine: Optional[TTSEngineType] = None,
                        voice: Optional[str] = None,
                        **kwargs) -> TTSResult:
        """
        Synthesiere Text mit spezifizierter oder aktiver Engine
        
        Args:
            text: Zu sprechender Text
            engine: Zu verwendende Engine (optional, nutzt aktive Engine)
            voice: Stimme (optional)
            **kwargs: Engine-spezifische Parameter
            
        Returns:
            TTSResult mit Audio-Daten und Metadaten
        """
        # Engine bestimmen
        target_engine = engine or self.active_engine

        if not target_engine or target_engine not in self.engines:
            return TTSResult(
                audio_data=None,
                success=False,
                error_message=f"Engine '{target_engine}' nicht verfügbar",
                engine_used=target_engine.value if target_engine else "unknown"
            )
            
        engine_instance = self.engines[target_engine]
        start_time = time.time()

        # Statistiken aktualisieren
        stats = self.engine_stats[target_engine]
        stats["total_requests"] += 1
        stats["last_used"] = time.time()

        chosen_voice = voice or engine_instance.config.voice
        logger.info(
            "TTS Synthese mit %s | Stimme: %s | Model-Dir: %s",
            target_engine.value,
            chosen_voice,
            engine_instance.config.model_dir,
        )
        
        try:
            # Synthese durchführen
            result = await engine_instance.synthesize(text, voice, **kwargs)
            
            # Statistiken aktualisieren
            if result.success:
                stats["successful_requests"] += 1
            else:
                stats["failed_requests"] += 1
                
            stats["total_processing_time_ms"] += result.processing_time_ms
            if stats["successful_requests"] > 0:
                stats["average_processing_time_ms"] = (
                    stats["total_processing_time_ms"] / stats["successful_requests"]
                )
                
            return result
            
        except Exception as e:
            # Fehler-Statistiken
            stats["failed_requests"] += 1
            processing_time = (time.time() - start_time) * 1000
            
            logger.error(f"TTS-Synthese fehlgeschlagen mit {target_engine.value}: {e}")
            
            return TTSResult(
                audio_data=None,
                success=False,
                error_message=str(e),
                processing_time_ms=processing_time,
                engine_used=target_engine.value
            )
            
    async def switch_engine(self, engine: TTSEngineType) -> bool:
        """
        Wechsle zu anderer TTS-Engine
        
        Args:
            engine: Ziel-Engine
            
        Returns:
            bool: True wenn Wechsel erfolgreich
        """
        if engine not in self.engines:
            logger.error(f"Engine '{engine.value}' nicht verfügbar")
            return False
            
        old_engine = self.active_engine
        self.active_engine = engine
        
        logger.info(f"🔄 Engine gewechselt: {old_engine.value if old_engine else 'None'} → {engine.value}")
        
        # Callbacks benachrichtigen
        await self._notify_engine_change(old_engine, engine)
        
        return True
        
    async def get_available_engines(self) -> List[Dict[str, Any]]:
        """Gib verfügbare Engines mit Informationen zurück"""
        engines_info = []
        
        for engine_type, engine in self.engines.items():
            info = engine.get_engine_info()
            info.update({
                "engine_type": engine_type.value,
                "is_active": engine_type == self.active_engine,
                "stats": self.engine_stats[engine_type].copy()
            })
            engines_info.append(info)
            
        return engines_info
        
    async def get_available_voices(self, engine: Optional[TTSEngineType] = None) -> Dict[str, List[str]]:
        """
        Gib verfügbare Stimmen zurück
        
        Args:
            engine: Spezifische Engine (optional, alle wenn None)
            
        Returns:
            Dict mit Engine-Namen als Keys und Stimmen-Listen als Values
        """
        voices = {}
        
        if engine:
            if engine in self.engines:
                voices[engine.value] = self.engines[engine].get_available_voices()
        else:
            for engine_type, engine_instance in self.engines.items():
                voices[engine_type.value] = engine_instance.get_available_voices()
                
        return voices
        
    async def set_voice(self, voice: str, engine: Optional[TTSEngineType] = None) -> bool:
        """
        Setze Stimme für Engine
        
        Args:
            voice: Stimme
            engine: Engine (optional, nutzt aktive Engine)
            
        Returns:
            bool: True wenn erfolgreich
        """
        target_engine = engine or self.active_engine
        
        if not target_engine or target_engine not in self.engines:
            return False
            
        return self.engines[target_engine].set_voice(voice)
        
    async def update_config(self, config_updates: Dict[str, Any], engine: Optional[TTSEngineType] = None) -> bool:
        """
        Aktualisiere Engine-Konfiguration
        
        Args:
            config_updates: Konfiguration-Updates
            engine: Engine (optional, nutzt aktive Engine)
            
        Returns:
            bool: True wenn erfolgreich
        """
        target_engine = engine or self.active_engine
        
        if not target_engine or target_engine not in self.engines:
            return False
            
        try:
            self.engines[target_engine].update_config(**config_updates)
            logger.info(f"Konfiguration aktualisiert für {target_engine.value}: {config_updates}")
            return True
        except Exception as e:
            logger.error(f"Fehler beim Update der Konfiguration: {e}")
            return False
            
    async def test_all_engines(self, test_text: str = "Test der Sprachsynthese") -> Dict[str, TTSResult]:
        """
        Teste alle verfügbaren Engines
        
        Args:
            test_text: Test-Text
            
        Returns:
            Dict mit Engine-Namen als Keys und TTSResult als Values
        """
        results = {}
        
        for engine_type, engine in self.engines.items():
            logger.info(f"Teste {engine_type.value} Engine...")
            result = await engine.test_synthesis(test_text)
            results[engine_type.value] = result
            
            if result.success:
                logger.info(f"✅ {engine_type.value}: {result.processing_time_ms:.1f}ms")
            else:
                logger.error(f"❌ {engine_type.value}: {result.error_message}")
                
        return results
        
    def get_current_engine(self) -> Optional[TTSEngineType]:
        """Gib aktuelle Engine zurück"""
        return self.active_engine
        
    def get_engine_stats(self) -> Dict[str, Dict[str, Any]]:
        """Gib Engine-Statistiken zurück"""
        return {
            engine_type.value: stats.copy() 
            for engine_type, stats in self.engine_stats.items()
        }
        
    def add_engine_change_callback(self, callback: callable):
        """Füge Callback für Engine-Wechsel hinzu"""
        self.engine_change_callbacks.append(callback)
        
    def remove_engine_change_callback(self, callback: callable):
        """Entferne Engine-Wechsel-Callback"""
        if callback in self.engine_change_callbacks:
            self.engine_change_callbacks.remove(callback)
            
    async def _notify_engine_change(self, old_engine: Optional[TTSEngineType], new_engine: TTSEngineType):
        """Benachrichtige über Engine-Wechsel"""
        for callback in self.engine_change_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(old_engine, new_engine)
                else:
                    callback(old_engine, new_engine)
            except Exception as e:
                logger.error(f"Fehler bei Engine-Change-Callback: {e}")
                
    async def cleanup(self):
        """Cleanup aller TTS-Engines"""
        logger.info("TTS-Manager Cleanup...")
        
        for engine_type, engine in self.engines.items():
            try:
                await engine.cleanup()
                logger.info(f"✅ {engine_type.value} Engine cleanup abgeschlossen")
            except Exception as e:
                logger.error(f"❌ Fehler beim {engine_type.value} cleanup: {e}")
                
        self.engines.clear()
        self.active_engine = None
        logger.info("🔄 TTS-Manager cleanup abgeschlossen")
        
    def __str__(self):
        active_name = self.active_engine.value if self.active_engine else "None"
        available_engines = [e.value for e in self.engines.keys()]
        return f"TTSManager(active={active_name}, available={available_engines})"
        
    def __repr__(self):
        return f"TTSManager(engines={list(self.engines.keys())}, active={self.active_engine})"

# Convenience-Funktionen für einfache Nutzung
def create_default_tts_manager() -> TTSManager:
    """Erstelle TTS-Manager mit Standard-Konfiguration"""
    return TTSManager()

async def quick_synthesize(text: str, engine: str = "piper", voice: Optional[str] = None) -> TTSResult:
    """
    Schnelle TTS-Synthese ohne Manager-Setup
    
    Args:
        text: Zu sprechender Text
        engine: Engine-Name ("piper" oder "kokoro")
        voice: Stimme (optional)
        
    Returns:
        TTSResult
    """
    manager = create_default_tts_manager()
    
    try:
        await manager.initialize()
        
        e=(engine or 'piper').lower()
        if e=='piper':
            engine_type=TTSEngineType.PIPER
        elif e=='kokoro':
            engine_type=TTSEngineType.KOKORO
        elif e=='zonos':
            engine_type=TTSEngineType.ZONOS
        else:
            engine_type=TTSEngineType.PIPER
        await manager.switch_engine(engine_type)
        
        return await manager.synthesize(text, voice=voice)
        
    finally:
        await manager.cleanup()