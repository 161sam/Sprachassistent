#!/usr/bin/env python3
"""
TTS Manager für Realtime-Engine-Switching
Ermöglicht dynamischen Wechsel zwischen Piper und Kokoro TTS
"""

import asyncio
import logging
import time
import os
from typing import Dict, Optional, List, Any, Union
from enum import Enum

# Initialize logger first
logger = logging.getLogger(__name__)

from .base_tts_engine import BaseTTSEngine, TTSConfig, TTSResult, TTSEngineError
from .piper_tts_engine import PiperTTSEngine

# Optional imports
# Use Zonos as default engine to match current project preference.
TTS_ENGINE = os.getenv("TTS_ENGINE", "zonos").lower()
KokoroTTSEngine = None  # Initialize as None

try:
    from .kokoro_tts_engine import KokoroTTSEngine
    logger.info("✅ Kokoro TTS Engine import successful")
except ImportError as e:
    logger.warning(f"KokoroTTSEngine nicht verfügbar")
    logger.info("💡 To enable Kokoro: pip install kokoro-onnx")
    KokoroTTSEngine = None
except Exception as e:
    logger.warning(f"Kokoro TTS Engine import failed: {e}")
    KokoroTTSEngine = None

# Optional Zonos import
try:
    from .engine_zonos import ZonosTTSEngine
    logger.info("✅ Zonos TTS Engine import successful")
except ImportError as e:
    logger.warning("ZonosTTSEngine nicht verfügbar")
    ZonosTTSEngine = None
except Exception as e:
    logger.warning(f"Zonos TTS Engine import failed: {e}")
    ZonosTTSEngine = None

class TTSEngineType(Enum):
    """Verfügbare TTS-Engine-Typen"""
    PIPER = "piper"
    KOKORO = "kokoro"
    ZONOS = "zonos"

class TTSManager:
    """
    TTS Manager für Multi-Engine-Support
    Ermöglicht dynamisches Switching zwischen verschiedenen TTS-Engines
    """
    
    def __init__(self):
        logger.info("Initialisiere TTS-Manager...")
        
        self.engines: Dict[str, BaseTTSEngine] = {}
        self.default_engine = None
        self.config = TTSConfig()
        
        # Engine-Verfügbarkeit prüfen
        self.available_engines = {
            "piper": PiperTTSEngine,
            "kokoro": KokoroTTSEngine,
            "zonos": ZonosTTSEngine
        }
        
        # Nur verfügbare Engines behalten
        self.available_engines = {
            name: engine_class 
            for name, engine_class in self.available_engines.items() 
            if engine_class is not None
        }
        
        logger.info(f"Verfügbare TTS-Engines: {list(self.available_engines.keys())}")
        
    async def initialize(self, piper_config: TTSConfig = None, kokoro_config: TTSConfig = None, 
                         zonos_config: TTSConfig = None, default_engine: TTSEngineType = None) -> bool:
        """Initialisiere TTS-Engines mit spezifischen Konfigurationen"""
        success_count = 0
        
        # Standard-Engine bestimmen
        target_engine_name = None
        if default_engine:
            target_engine_name = default_engine.value
        else:
            target_engine_name = TTS_ENGINE
            
        # Engine-Konfigurationen zuordnen
        engine_configs = {}
        if piper_config and "piper" in self.available_engines:
            engine_configs["piper"] = piper_config
        if kokoro_config and "kokoro" in self.available_engines:
            engine_configs["kokoro"] = kokoro_config
        if zonos_config and "zonos" in self.available_engines:
            engine_configs["zonos"] = zonos_config
            
        # Priorisiere die Standard-Engine
        engine_priority = []
        if target_engine_name in engine_configs:
            engine_priority.append(target_engine_name)
        for engine_name in engine_configs.keys():
            if engine_name not in engine_priority:
                engine_priority.append(engine_name)
                
        # Fallback-Konfigurationen für nicht bereitgestellte Engines
        for engine_name in self.available_engines.keys():
            if engine_name not in engine_configs:
                logger.info(f"Erstelle Fallback-Konfiguration für {engine_name}")
                fallback_config = TTSConfig(
                    engine_type=engine_name,
                    model_path="",
                    voice="default",
                    speed=1.0,
                    volume=1.0,
                    language="de",
                    sample_rate=22050
                )
                engine_configs[engine_name] = fallback_config
                if engine_name not in engine_priority:
                    engine_priority.append(engine_name)
                
        # Engines initialisieren
        for engine_name in engine_priority:
            if engine_name not in self.available_engines:
                continue
                
            try:
                logger.info(f"Initialisiere {engine_name.title()} TTS Engine...")
                
                engine_class = self.available_engines[engine_name]
                engine_config = engine_configs[engine_name]
                engine = engine_class(engine_config)
                
                # Engine initialisieren mit Timeout
                try:
                    init_result = await asyncio.wait_for(engine.initialize(), timeout=30.0)
                    if init_result:
                        self.engines[engine_name] = engine
                        success_count += 1
                        logger.info(f"✅ {engine_name.title()} TTS erfolgreich initialisiert")
                        
                        # Erste erfolgreiche Engine als Standard setzen
                        if self.default_engine is None:
                            self.default_engine = engine_name
                            logger.info(f"🎯 Standard-Engine: {engine_name}")
                    else:
                        logger.warning(f"❌ {engine_name.title()} TTS Initialisierung fehlgeschlagen")
                except asyncio.TimeoutError:
                    logger.error(f"⏰ {engine_name.title()} TTS Initialisierung timeout (30s) - überspringe...")
                    continue
                    
            except Exception as e:
                logger.error(f"❌ {engine_name.title()} TTS Fehler: {e}")
                continue
        
        if success_count > 0:
            logger.info(f"✅ TTS-Manager initialisiert mit {success_count} Engine(s)")
            return True
        else:
            logger.error("❌ Keine TTS-Engine verfügbar!")
            return False
    
    async def synthesize(self, text: str, engine: str = None, voice: str = None, **kwargs) -> TTSResult:
        """Synthesiere Text mit gewünschter Engine"""
        target_engine = engine or self.default_engine
        
        if not target_engine or target_engine not in self.engines:
            return TTSResult(
                audio_data=None,
                success=False,
                error_message=f"Engine '{target_engine}' nicht verfügbar",
                engine_used=target_engine or "none"
            )
        
        try:
            return await self.engines[target_engine].synthesize(text, voice, **kwargs)
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
                # Fallback: Voice in Config setzen
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
