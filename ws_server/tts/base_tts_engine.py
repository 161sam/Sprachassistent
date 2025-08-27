#!/usr/bin/env python3
"""
Abstrakte Basis-Klasse für TTS-Engines
Ermöglicht einheitliche Schnittstelle für verschiedene TTS-Systeme
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class TTSConfig:
    """Konfiguration für TTS-Engines"""
    engine_type: str = "piper"  # Default engine type
    model_path: str = "models/piper/default.onnx"  # Default model path
    voice: str = "default"  # Default voice
    speed: float = 1.0
    volume: float = 1.0
    sample_rate: int = 22050
    language: str = "de"
    model_dir: str = "models"
    
    # Engine-spezifische Parameter
    engine_params: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.engine_params is None:
            self.engine_params = {}

@dataclass
class TTSResult:
    """Ergebnis einer TTS-Synthese"""
    audio_data: Optional[bytes]
    success: bool
    error_message: Optional[str] = None
    processing_time_ms: float = 0.0
    voice_used: str = ""
    engine_used: str = ""
    
    # Metadaten
    sample_rate: int = 22050
    audio_format: str = "wav"
    audio_length_ms: float = 0.0

class BaseTTSEngine(ABC):
    """Abstrakte Basis-Klasse für alle TTS-Engines"""
    
    def __init__(self, config: TTSConfig):
        self.config = config
        self.is_initialized = False
        self.supported_voices: List[str] = []
        self.supported_languages: List[str] = []
        self.engine_name = self.__class__.__name__
        
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialisiere die TTS-Engine"""
        # TODO: raise NotImplementedError instead of pass
        #       (see TODO-Index.md: Backend/Base TTS Engine)
        pass
        
    @abstractmethod
    async def synthesize(self, text: str, voice: Optional[str] = None, **kwargs) -> TTSResult:
        """
        Synthesiere Text zu Audio
        
        Args:
            text: Zu sprechender Text
            voice: Stimme (optional, nutzt config.voice als Default)
            **kwargs: Engine-spezifische Parameter
            
        Returns:
            TTSResult mit Audio-Daten und Metadaten
        """
        # TODO: raise NotImplementedError instead of pass
        #       (see TODO-Index.md: Backend/Base TTS Engine)
        pass
        
    @abstractmethod
    async def cleanup(self):
        """Cleanup-Ressourcen der Engine"""
        # TODO: raise NotImplementedError instead of pass
        #       (see TODO-Index.md: Backend/Base TTS Engine)
        pass
        
    @abstractmethod
    def get_available_voices(self) -> List[str]:
        """Gib verfügbare Stimmen zurück"""
        return self.supported_voices.copy()
        
    @abstractmethod
    def get_engine_info(self) -> Dict[str, Any]:
        """Gib Engine-Informationen zurück"""
        # TODO: raise NotImplementedError instead of pass
        #       (see TODO-Index.md: Backend/Base TTS Engine)
        pass
        
    def validate_text(self, text: str) -> tuple[bool, str]:
        """Validiere Input-Text"""
        if not text or not text.strip():
            return False, "Text ist leer"
            
        if len(text) > 5000:  # Maximal 5000 Zeichen
            return False, "Text zu lang (max. 5000 Zeichen)"
            
        return True, ""
        
    def get_config(self) -> TTSConfig:
        """Gib aktuelle Konfiguration zurück"""
        return self.config
        
    def update_config(self, **kwargs):
        """Update Konfiguration"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                logger.debug(f"Updated {self.engine_name} config: {key} = {value}")
            else:
                logger.warning(f"Unknown config parameter: {key}")
                
    def supports_voice(self, voice: str) -> bool:
        """Prüfe, ob Stimme unterstützt wird"""
        return voice in self.supported_voices
        
    def supports_language(self, language: str) -> bool:
        """Prüfe, ob Sprache unterstützt wird"""
        return language in self.supported_languages
        
    async def test_synthesis(self, test_text: str = "Test") -> TTSResult:
        """Teste TTS-Engine mit einem kurzen Text"""
        if not self.is_initialized:
            await self.initialize()
            
        return await self.synthesize(test_text)
        
    def __str__(self):
        return f"{self.engine_name}(voice={self.config.voice}, lang={self.config.language})"
        
    def __repr__(self):
        return f"{self.engine_name}(config={self.config})"

class TTSEngineError(Exception):
    """Basis-Exception für TTS-Engine-Fehler"""
    pass

class TTSInitializationError(TTSEngineError):
    """Exception für Initialisierungsfehler"""
    pass

class TTSSynthesisError(TTSEngineError):
    """Exception für Synthese-Fehler"""
    pass

class TTSVoiceNotSupportedError(TTSEngineError):
    """Exception für nicht unterstützte Stimmen"""
    pass
