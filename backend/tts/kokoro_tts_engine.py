#!/usr/bin/env python3
"""
Kokoro TTS Engine Implementation
Kompakte und effiziente TTS-Engine basierend auf Kokoro-82M
"""

import asyncio
import tempfile
import os
import time
import logging
import numpy as np
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from concurrent.futures import ThreadPoolExecutor

from .base_tts_engine import BaseTTSEngine, TTSConfig, TTSResult, TTSInitializationError, TTSSynthesisError

if TYPE_CHECKING:  # pragma: no cover - used for type hints only
    from kokoro_onnx import Kokoro

logger = logging.getLogger(__name__)

try:
    from kokoro_onnx import Kokoro
    import soundfile as sf
    KOKORO_AVAILABLE = True
except ImportError:
    KOKORO_AVAILABLE = False
    logger.warning("Kokoro TTS nicht verfügbar - installiere: pip install kokoro-onnx soundfile")

class KokoroTTSEngine(BaseTTSEngine):
    """Kokoro TTS Engine für kompakte und schnelle Sprachsynthese"""
    
    def __init__(self, config: TTSConfig):
        super().__init__(config)
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="KokoroTTS")
        self.kokoro_model = None
        
        # Kokoro-spezifische Konfiguration
        self.model_file = "kokoro-v1.0.int8.onnx"  # Quantisiertes Modell (~80MB)
        self.voices_file = "voices-v1.0.bin"
        
        # Verfügbare Stimmen (Kokoro unterstützt verschiedene Sprachen)
        self.supported_voices = [
            # Englische Stimmen
            "af_sarah", "af_michael", "af_heart", "af_sky", "af_alice",
            "af_nova", "af_alloy", "af_onyx", "af_echo", "af_fable", "af_shimmer",
            # Deutsche Stimmen (wenn verfügbar)
            "de_female", "de_male",
            # Weitere internationale Stimmen
            "bf_emma", "bf_isabella", "am_adam", "am_daniel"
        ]
        
        self.supported_languages = ["en", "en-US", "de", "de-DE", "multi"]
        
        # Standard-Stimme je nach Sprache
        self.default_voices = {
            "de": "af_sarah",  # Bis deutsche Stimmen verfügbar
            "en": "af_sarah",
            "multi": "af_heart"
        }
        
    async def initialize(self) -> bool:
        """Initialisiere Kokoro TTS Engine"""
        if not KOKORO_AVAILABLE:
            raise TTSInitializationError("Kokoro TTS Bibliothek nicht verfügbar")
            
        try:
            # Modell- und Voice-Dateien suchen
            model_path = self._find_model_file(self.model_file)
            voices_path = self._find_model_file(self.voices_file)
            
            if not model_path or not voices_path:
                # Versuche Download-URLs zu laden
                await self._ensure_model_files()
                model_path = self._find_model_file(self.model_file)
                voices_path = self._find_model_file(self.voices_file)
                
            if not model_path or not voices_path:
                raise TTSInitializationError("Kokoro-Modell-Dateien nicht gefunden")
                
            # Initialisiere Kokoro-Modell im Thread Pool
            loop = asyncio.get_event_loop()
            self.kokoro_model = await loop.run_in_executor(
                self.executor,
                self._load_kokoro_model,
                model_path,
                voices_path
            )
            
            self.is_initialized = True
            logger.info(f"Kokoro TTS initialisiert mit Stimme: {self.config.voice}")
            return True
            
        except Exception as e:
            logger.error(f"Kokoro TTS Initialisierung fehlgeschlagen: {e}")
            self.is_initialized = False
            return False
            
    def _load_kokoro_model(self, model_path: str, voices_path: str) -> "Kokoro":
        """Lade Kokoro-Modell synchron"""
        try:
            return Kokoro(model_path, voices_path)
        except Exception as e:
            logger.error(f"Fehler beim Laden des Kokoro-Modells: {e}")
            raise TTSInitializationError(f"Kokoro-Modell konnte nicht geladen werden: {e}")
            
    async def synthesize(self, text: str, voice: Optional[str] = None, **kwargs) -> TTSResult:
        """Synthesiere Text mit Kokoro TTS"""
        start_time = time.time()
        
        # Validierung
        is_valid, error_msg = self.validate_text(text)
        if not is_valid:
            return TTSResult(
                audio_data=None,
                success=False,
                error_message=error_msg,
                engine_used="Kokoro"
            )
            
        if not self.is_initialized:
            await self.initialize()
            
        # Stimme bestimmen
        target_voice = voice or self.config.voice
        if not self.supports_voice(target_voice):
            # Fallback auf Standard-Stimme für Sprache
            lang = self.config.language.split('-')[0]
            target_voice = self.default_voices.get(lang, "af_sarah")
            logger.warning(f"Stimme '{voice}' nicht unterstützt, verwende '{target_voice}'")
            
        try:
            audio_data = await self._synthesize_with_kokoro(text, target_voice, **kwargs)
            
            processing_time = (time.time() - start_time) * 1000
            
            return TTSResult(
                audio_data=audio_data,
                success=True,
                processing_time_ms=processing_time,
                voice_used=target_voice,
                engine_used="Kokoro",
                sample_rate=24000,  # Kokoro-Standard
                audio_format="wav",
                audio_length_ms=self._estimate_audio_length(audio_data) if audio_data else 0
            )
            
        except Exception as e:
            logger.error(f"Kokoro TTS Synthese fehlgeschlagen: {e}")
            return TTSResult(
                audio_data=None,
                success=False,
                error_message=str(e),
                processing_time_ms=(time.time() - start_time) * 1000,
                engine_used="Kokoro"
            )
            
    async def _synthesize_with_kokoro(self, text: str, voice: str, **kwargs) -> Optional[bytes]:
        """Interne Synthese mit Kokoro"""
        if not self.kokoro_model:
            raise TTSSynthesisError("Kokoro-Modell nicht initialisiert")
            
        loop = asyncio.get_event_loop()
        
        return await loop.run_in_executor(
            self.executor,
            self._kokoro_synthesis_sync,
            text,
            voice,
            kwargs
        )
        
    def _kokoro_synthesis_sync(self, text: str, voice: str, options: Dict) -> Optional[bytes]:
        """Synchrone Kokoro-Synthese im Thread Pool"""
        try:
            # Geschwindigkeit und Sprache aus Optionen
            speed = options.get('speed', self.config.speed)
            lang = options.get('language', self.config.language)
            
            # Sprach-Code für Kokoro anpassen
            if lang.startswith('de'):
                lang_code = "de-de"  # Falls unterstützt
            else:
                lang_code = "en-us"  # Standard
                
            # Kokoro-Synthese
            samples, sample_rate = self.kokoro_model.create(
                text=text,
                voice=voice,
                speed=speed,
                lang=lang_code
            )
            
            # Audio zu WAV konvertieren
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                temp_path = temp_file.name
                
            # Soundfile verwenden um WAV zu schreiben
            sf.write(temp_path, samples, sample_rate)
            
            # Audio-Daten lesen
            with open(temp_path, 'rb') as f:
                audio_data = f.read()
                
            # Cleanup
            os.unlink(temp_path)
            
            return audio_data
            
        except Exception as e:
            logger.error(f"Kokoro-Synthese-Fehler: {e}")
            return None
            
    def _find_model_file(self, filename: str) -> Optional[str]:
        """Suche Modell-Datei in verschiedenen Pfaden"""
        search_paths = [
            f"./{filename}",  # Aktuelles Verzeichnis
            f"./models/{filename}",  # Models-Unterverzeichnis
            f"~/.local/share/kokoro/{filename}",  # User-Verzeichnis
            f"/usr/share/kokoro/{filename}",  # System-Verzeichnis
            f"~/Downloads/{filename}",  # Downloads
            os.path.join(os.path.dirname(__file__), filename),  # TTS-Verzeichnis
            os.path.join(os.path.dirname(__file__), "models", filename)  # TTS/models
        ]
        
        for path in search_paths:
            expanded_path = os.path.expanduser(path)
            if os.path.exists(expanded_path):
                logger.debug(f"Kokoro-Modell gefunden: {expanded_path}")
                return expanded_path
                
        return None
        
    async def _ensure_model_files(self):
        """Stelle sicher, dass Modell-Dateien verfügbar sind"""
        logger.info("Lade Kokoro-Modell-Dateien herunter...")
        
        # URLs für Modell-Dateien
        model_url = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.int8.onnx"
        voices_url = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"
        
        # Download-Verzeichnis erstellen
        download_dir = os.path.expanduser("~/.local/share/kokoro")
        os.makedirs(download_dir, exist_ok=True)
        
        try:
            import aiohttp
            import aiofiles
            
            async with aiohttp.ClientSession() as session:
                # Modell-Datei herunterladen
                model_path = os.path.join(download_dir, self.model_file)
                if not os.path.exists(model_path):
                    logger.info(f"Lade {self.model_file} herunter...")
                    await self._download_file(session, model_url, model_path)
                    
                # Voices-Datei herunterladen
                voices_path = os.path.join(download_dir, self.voices_file)
                if not os.path.exists(voices_path):
                    logger.info(f"Lade {self.voices_file} herunter...")
                    await self._download_file(session, voices_url, voices_path)
                    
        except ImportError:
            logger.warning("aiohttp/aiofiles nicht verfügbar für Download")
            raise TTSInitializationError("Modell-Dateien müssen manuell heruntergeladen werden")
        except Exception as e:
            logger.error(f"Download fehlgeschlagen: {e}")
            raise TTSInitializationError(f"Modell-Download fehlgeschlagen: {e}")
            
    async def _download_file(self, session, url: str, path: str):
        """Lade Datei herunter"""
        try:
            async with session.get(url) as response:
                response.raise_for_status()
                
                async with aiofiles.open(path, 'wb') as f:
                    async for chunk in response.content.iter_chunked(8192):
                        await f.write(chunk)
                        
            logger.info(f"Download abgeschlossen: {path}")
            
        except Exception as e:
            if os.path.exists(path):
                os.unlink(path)  # Unvollständige Datei löschen
            raise e
            
    def _estimate_audio_length(self, audio_data: bytes) -> float:
        """Schätze Audio-Länge in Millisekunden"""
        if not audio_data or len(audio_data) < 44:  # WAV-Header
            return 0.0
            
        # Einfache Schätzung basierend auf Datei-Größe
        # 44-Byte WAV-Header + 2 Bytes pro Sample * Sample Rate (24000 für Kokoro)
        audio_bytes = len(audio_data) - 44
        samples = audio_bytes // 2  # 16-bit Audio
        return (samples / 24000) * 1000  # Kokoro verwendet 24kHz
        
    async def cleanup(self):
        """Cleanup Kokoro TTS Ressourcen"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)
        self.kokoro_model = None
        logger.info("Kokoro TTS Engine cleanup abgeschlossen")
        
    def get_available_voices(self) -> List[str]:
        """Gib verfügbare Stimmen zurück"""
        return self.supported_voices.copy()
        
    def get_engine_info(self) -> Dict[str, Any]:
        """Gib Engine-Informationen zurück"""
        return {
            "name": "Kokoro TTS",
            "version": "1.0 (82M)",
            "supported_voices": self.supported_voices,
            "supported_languages": self.supported_languages,
            "current_voice": self.config.voice,
            "model_size": "~80MB (quantisiert)",
            "is_initialized": self.is_initialized,
            "model_available": KOKORO_AVAILABLE,
            "features": [
                "Kompakte Modell-Größe (~80MB)",
                "Mehrsprachig",
                "Natürliche Stimmen",
                "Schnelle Inferenz",
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
        logger.info(f"Stimme geändert von '{old_voice}' zu '{voice}'")
        return True
        
    def get_voice_recommendations(self, language: str = "de") -> List[str]:
        """Gib empfohlene Stimmen für Sprache zurück"""
        if language.startswith('de'):
            return ["af_sarah", "af_heart", "af_sky"]  # Bis deutsche Stimmen verfügbar
        elif language.startswith('en'):
            return ["af_sarah", "af_nova", "af_alloy", "af_heart"]
        else:
            return ["af_sarah", "af_heart"]  # Universal
