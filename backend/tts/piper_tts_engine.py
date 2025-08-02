#!/usr/bin/env python3
"""
Piper TTS Engine Implementation
Optimiert für deutsche Sprache mit hoher Qualität
"""

import asyncio
import subprocess
import tempfile
import os
import time
import logging
from typing import Optional, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor

from .base_tts_engine import BaseTTSEngine, TTSConfig, TTSResult, TTSInitializationError, TTSSynthesisError

logger = logging.getLogger(__name__)

class PiperTTSEngine(BaseTTSEngine):
    """Piper TTS Engine für deutsche Sprachsynthese"""
    
    def __init__(self, config: TTSConfig):
        super().__init__(config)
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="PiperTTS")
        self.model_cache = {}
        
        # Piper-spezifische Konfiguration
        self.piper_executable = "piper"  # Pfad zur Piper-Binary
        
        # Verfügbare deutsche Stimmen
        self.supported_voices = [
            "de-thorsten-low",
            "de-thorsten-medium", 
            "de-thorsten-high",
            "de-kerstin-low",
            "de-kerstin-medium",
            "de-eva_k-low",
            "de-eva_k-medium",
            "de-ramona-low",
            "de-karlsson-low"
        ]
        
        self.supported_languages = ["de", "de-DE"]
        
        # Voice-zu-Modell-Mapping
        self.voice_model_mapping = {
            "de-thorsten-low": "de_DE-thorsten-low.onnx",
            "de-thorsten-medium": "de_DE-thorsten-medium.onnx",
            "de-thorsten-high": "de_DE-thorsten-high.onnx",
            "de-kerstin-low": "de_DE-kerstin-low.onnx",
            "de-kerstin-medium": "de_DE-kerstin-medium.onnx",
            "de-eva_k-low": "de_DE-eva_k-low.onnx",
            "de-eva_k-medium": "de_DE-eva_k-medium.onnx",
            "de-ramona-low": "de_DE-ramona-low.onnx",
            "de-karlsson-low": "de_DE-karlsson-low.onnx"
        }
        
    async def initialize(self) -> bool:
        """Initialisiere Piper TTS Engine"""
        try:
            # Prüfe ob Piper verfügbar ist
            result = await self._run_command([self.piper_executable, "--version"])
            if result.returncode != 0:
                raise TTSInitializationError("Piper executable nicht gefunden")
                
            # Prüfe Modell-Verfügbarkeit
            model_path = self._get_model_path(self.config.voice)
            if not os.path.exists(model_path):
                logger.warning(f"Modell nicht gefunden: {model_path}")
                # Versuche Standard-Modell
                default_model = os.path.expanduser("~/.local/share/piper/de-thorsten-low.onnx")
                if os.path.exists(default_model):
                    logger.info(f"Verwende Standard-Modell: {default_model}")
                    self.config.model_path = default_model
                    self.config.voice = "de-thorsten-low"
                else:
                    raise TTSInitializationError(f"Kein Piper-Modell verfügbar")
                    
            self.is_initialized = True
            logger.info(f"Piper TTS initialisiert mit Stimme: {self.config.voice}")
            return True
            
        except Exception as e:
            logger.error(f"Piper TTS Initialisierung fehlgeschlagen: {e}")
            self.is_initialized = False
            return False
            
    async def synthesize(self, text: str, voice: Optional[str] = None, **kwargs) -> TTSResult:
        """Synthesiere Text mit Piper TTS"""
        start_time = time.time()
        
        # Validierung
        is_valid, error_msg = self.validate_text(text)
        if not is_valid:
            return TTSResult(
                audio_data=None,
                success=False,
                error_message=error_msg,
                engine_used="Piper"
            )
            
        if not self.is_initialized:
            await self.initialize()
            
        # Stimme bestimmen
        target_voice = voice or self.config.voice
        if not self.supports_voice(target_voice):
            logger.warning(f"Stimme '{target_voice}' nicht unterstützt, verwende '{self.config.voice}'")
            target_voice = self.config.voice
            
        try:
            audio_data = await self._synthesize_with_piper(text, target_voice, **kwargs)
            
            processing_time = (time.time() - start_time) * 1000
            
            return TTSResult(
                audio_data=audio_data,
                success=True,
                processing_time_ms=processing_time,
                voice_used=target_voice,
                engine_used="Piper",
                sample_rate=self.config.sample_rate,
                audio_format="wav",
                audio_length_ms=self._estimate_audio_length(audio_data) if audio_data else 0
            )
            
        except Exception as e:
            logger.error(f"Piper TTS Synthese fehlgeschlagen: {e}")
            return TTSResult(
                audio_data=None,
                success=False,
                error_message=str(e),
                processing_time_ms=(time.time() - start_time) * 1000,
                engine_used="Piper"
            )
            
    async def _synthesize_with_piper(self, text: str, voice: str, **kwargs) -> Optional[bytes]:
        """Interne Synthese mit Piper"""
        loop = asyncio.get_event_loop()
        
        return await loop.run_in_executor(
            self.executor,
            self._piper_synthesis_sync,
            text,
            voice,
            kwargs
        )
        
    def _piper_synthesis_sync(self, text: str, voice: str, options: Dict) -> Optional[bytes]:
        """Synchrone Piper-Synthese im Thread Pool"""
        try:
            # Temporary Dateien erstellen
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as output_file:
                output_path = output_file.name
                
            # Modell-Pfad bestimmen
            model_path = self._get_model_path(voice)
            
            # Piper-Kommando zusammenstellen
            cmd = [
                self.piper_executable,
                "--model", model_path,
                "--output_file", output_path,
                "--text", text
            ]
            
            # Optional: Geschwindigkeit anpassen
            if self.config.speed != 1.0:
                cmd.extend(["--length_scale", str(1.0 / self.config.speed)])
                
            # Optional: Sample Rate
            if self.config.sample_rate != 22050:
                cmd.extend(["--sample_rate", str(self.config.sample_rate)])
                
            # Engine-spezifische Parameter
            for key, value in self.config.engine_params.items():
                if key in ["noise_scale", "noise_w", "length_scale"]:
                    cmd.extend([f"--{key}", str(value)])
                    
            # Piper ausführen
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,  # 30s Timeout
                cwd=os.path.dirname(model_path) if os.path.dirname(model_path) else None
            )
            
            if result.returncode == 0 and os.path.exists(output_path):
                # Audio-Daten lesen
                with open(output_path, 'rb') as f:
                    audio_data = f.read()
                    
                # Cleanup
                os.unlink(output_path)
                
                return audio_data
            else:
                logger.error(f"Piper-Fehler: {result.stderr}")
                if os.path.exists(output_path):
                    os.unlink(output_path)
                return None
                
        except subprocess.TimeoutExpired:
            logger.error("Piper TTS Timeout")
            return None
        except Exception as e:
            logger.error(f"Piper-Synthese-Fehler: {e}")
            return None
            
    def _get_model_path(self, voice: str) -> str:
        """Bestimme Modell-Pfad für Stimme"""
        if self.config.model_path and os.path.exists(self.config.model_path):
            return self.config.model_path
            
        # Standard-Pfade prüfen
        model_filename = self.voice_model_mapping.get(voice, f"{voice}.onnx")
        
        standard_paths = [
            f"~/.local/share/piper/{model_filename}",
            f"./models/{model_filename}",
            f"/usr/share/piper/{model_filename}",
            model_filename  # Falls absoluter Pfad
        ]
        
        for path in standard_paths:
            expanded_path = os.path.expanduser(path)
            if os.path.exists(expanded_path):
                return expanded_path
                
        # Fallback: Standard-Modell
        fallback = os.path.expanduser("~/.local/share/piper/de-thorsten-low.onnx")
        if os.path.exists(fallback):
            logger.warning(f"Verwende Fallback-Modell: {fallback}")
            return fallback
            
        raise TTSInitializationError(f"Kein Piper-Modell für Stimme '{voice}' gefunden")
        
    async def _run_command(self, cmd: List[str]) -> subprocess.CompletedProcess:
        """Führe Kommando asynchron aus"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            lambda: subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        )
        
    def _estimate_audio_length(self, audio_data: bytes) -> float:
        """Schätze Audio-Länge in Millisekunden"""
        if not audio_data or len(audio_data) < 44:  # WAV-Header
            return 0.0
            
        # Einfache Schätzung basierend auf Datei-Größe
        # 44-Byte WAV-Header + 2 Bytes pro Sample * Sample Rate
        audio_bytes = len(audio_data) - 44
        samples = audio_bytes // 2  # 16-bit Audio
        return (samples / self.config.sample_rate) * 1000
        
    async def cleanup(self):
        """Cleanup Piper TTS Ressourcen"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)
        self.model_cache.clear()
        logger.info("Piper TTS Engine cleanup abgeschlossen")
        
    def get_available_voices(self) -> List[str]:
        """Gib verfügbare Stimmen zurück"""
        return self.supported_voices.copy()
        
    def get_engine_info(self) -> Dict[str, Any]:
        """Gib Engine-Informationen zurück"""
        return {
            "name": "Piper TTS",
            "version": "1.0",
            "supported_voices": self.supported_voices,
            "supported_languages": self.supported_languages,
            "current_voice": self.config.voice,
            "model_path": self.config.model_path,
            "is_initialized": self.is_initialized,
            "features": [
                "Hochqualitative deutsche Stimmen",
                "Geschwindigkeitsanpassung",
                "Verschiedene Stimm-Modelle",
                "Offline-Verarbeitung"
            ]
        }
        
    def set_voice(self, voice: str) -> bool:
        """Ändere aktuelle Stimme"""
        if not self.supports_voice(voice):
            logger.error(f"Stimme '{voice}' wird nicht unterstützt")
            return False
            
        old_voice = self.config.voice
        self.config.voice = voice
        
        # Aktualisiere Modell-Pfad
        try:
            self.config.model_path = self._get_model_path(voice)
            logger.info(f"Stimme geändert von '{old_voice}' zu '{voice}'")
            return True
        except Exception as e:
            logger.error(f"Fehler beim Ändern der Stimme: {e}")
            self.config.voice = old_voice  # Rollback
            return False
