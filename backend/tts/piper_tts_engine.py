#!/usr/bin/env python3
"""
Piper TTS Engine Implementation
Optimiert für deutsche Sprache mit hoher Qualität
"""

import asyncio
import io
import os
import time
import logging
import wave
from typing import Optional, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor
from piper import PiperVoice, SynthesisConfig
from .voice_aliases import resolve_voice_alias

from .base_tts_engine import BaseTTSEngine, TTSConfig, TTSResult, TTSInitializationError

logger = logging.getLogger(__name__)

class PiperTTSEngine(BaseTTSEngine):
    """Piper TTS Engine für deutsche Sprachsynthese"""
    
    def __init__(self, config: TTSConfig):
        super().__init__(config)
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="PiperTTS")
        self.voice_cache: Dict[str, PiperVoice] = {}
        
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
            "de-karlsson-low",
            "en-amy-low"
        ]

        self.supported_languages = ["de", "de-DE", "en", "en-US"]

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
            "de-karlsson-low": "de_DE-karlsson-low.onnx",
            "en-amy-low": "en_US-amy-low.onnx"
        }

    def supports_voice(self, voice: str) -> bool:  # type: ignore[override]
        canonical = resolve_voice_alias(voice)
        return voice in self.supported_voices or canonical in self.supported_voices

    def _list_available_models(self, bases: List[str]) -> List[str]:
        models = set()
        for b in bases:
            p = os.path.join(b, "piper")
            try:
                for fn in os.listdir(p):
                    if fn.endswith(".onnx"):
                        models.add(os.path.splitext(fn)[0])
            except FileNotFoundError:
                continue
            except Exception:
                continue
        return sorted(models)
        
    async def initialize(self) -> bool:
        # --- BEGIN: robust local Piper model resolver ---
        import os
        import logging
        log = logging.getLogger("backend.tts.piper_tts_engine")
        # Stimmenname aus Instanz, ENV oder Default ziehen
        voice = resolve_voice_alias(getattr(self, "voice", None) or os.getenv("TTS_VOICE") or "de_DE-thorsten-low")
        # Alias-Varianten testen
        cand_names = list(dict.fromkeys([
            voice,
            voice.replace("de_DE-", "de-"),
            voice.replace("de-", "de_DE-"),
        ]))
        # Mögliche Basisverzeichnisse (in Reihenfolge) sammeln
        bases = []
        for envk in ("TTS_MODEL_DIR", "MODELS_DIR"):
            v = os.getenv(envk)
            if v:
                bases.append(v)
        # Fallback: <repo>/models
        bases.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "models"))
        tried = []
        for b in bases:
            for name in cand_names:
                onnx = os.path.join(b, "piper", f"{name}.onnx")
                js   = os.path.join(b, "piper", f"{name}.onnx.json")
                tried.append((onnx, js))
                if os.path.isfile(onnx) and os.path.isfile(js):
                    log.info(f"Piper: benutze lokales Modell: {onnx}")
                    self.model_path = onnx
                    self.config_path = js
                    self.voice_ready = True
                    # Früh raus – Rest der Init überspringen
                    return True
        log.warning("Piper: kein lokales Modell gefunden; geprüft:")
        for onnx, js in tried:
            log.warning(f"  - {onnx} | {js}")
        available = self._list_available_models(bases)
        if available:
            log.warning("Verfügbare Modelle: %s", ", ".join(available))
        # --- END: robust local Piper model resolver ---
        # --- BEGIN local model fallback for direct files ---
        import os
        import logging
        logger = logging.getLogger("backend.tts.piper_tts_engine")
        base = os.getenv("TTS_MODEL_DIR") or os.getenv("MODELS_DIR") or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "models")
        voice = (os.getenv("TTS_VOICE") or "").strip()
        def _resolve_local_files(v):
            v = resolve_voice_alias(v)
            names = [v, v.replace("de_DE-", "de-"), v.replace("de-", "de_DE-")]
            for name in names:
                onnx  = os.path.join(base, "piper", f"{name}.onnx")
                js    = os.path.join(base, "piper", f"{name}.onnx.json")
                if os.path.isfile(onnx) and os.path.isfile(js):
                    return onnx, js
            return None, None
        if voice:
            onnx, js = _resolve_local_files(voice)
            if onnx and js:
                logger.info(f"Piper: benutze lokales Modell: {onnx}")
                self.model_path = onnx
                self.config_path = js
                self.voice_ready = True
                return True
        # --- END local model fallback ---
        """Initialisiere Piper TTS Engine"""
        try:
            model_path = self._get_model_path(self.config.voice)
            loop = asyncio.get_event_loop()
            voice = await loop.run_in_executor(
                self.executor,
                PiperVoice.load,
                model_path
            )
            self.voice_cache[self.config.voice] = voice
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
            audio_data, sr = await self._synthesize_with_piper(text, target_voice, **kwargs)

            processing_time = (time.time() - start_time) * 1000

            return TTSResult(
                audio_data=audio_data,
                success=True,
                processing_time_ms=processing_time,
                voice_used=target_voice,
                engine_used="Piper",
                sample_rate=sr,
                audio_format="wav",
                audio_length_ms=self._estimate_audio_length(audio_data, sr) if audio_data else 0
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
            
    async def _synthesize_with_piper(self, text: str, voice: str, **kwargs) -> tuple[Optional[bytes], int]:
        """Interne Synthese mit Piper"""
        loop = asyncio.get_event_loop()

        return await loop.run_in_executor(
            self.executor,
            self._piper_synthesis_sync,
            text,
            voice,
            kwargs
        )

    def _piper_synthesis_sync(self, text: str, voice: str, options: Dict) -> tuple[Optional[bytes], int]:
        """Synchrone Piper-Synthese im Thread Pool"""
        try:
            voice_obj = self.voice_cache.get(voice)
            if voice_obj is None:
                model_path = self._get_model_path(voice)
                voice_obj = PiperVoice.load(model_path)
                self.voice_cache[voice] = voice_obj

            speed = options.get('speed', self.config.speed)
            volume = options.get('volume', self.config.volume)
            syn_cfg = SynthesisConfig(length_scale=1.0 / speed, volume=volume)

            buffer = io.BytesIO()
            with wave.open(buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(voice_obj.config.sample_rate)
                for chunk in voice_obj.synthesize(text, syn_config=syn_cfg):
                    wav_file.writeframes(chunk.audio_int16_bytes)

            return buffer.getvalue(), voice_obj.config.sample_rate
        except Exception as e:
            logger.error(f"Piper-Synthese-Fehler: {e}")
            return None, self.config.sample_rate
            
    def _get_model_path(self, voice: str) -> str:
        """Bestimme Modell-Pfad für Stimme"""
        if self.config.model_path and os.path.exists(self.config.model_path):
            return self.config.model_path

        voice = resolve_voice_alias(voice)

        # Standard-Pfade prüfen
        model_filename = self.voice_model_mapping.get(voice, f"{voice}.onnx")

        standard_paths = [
            os.path.join(self.config.model_dir, model_filename),
            f"~/.local/share/piper/{model_filename}",
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
        
    def _estimate_audio_length(self, audio_data: bytes, sample_rate: int) -> float:
        """Schätze Audio-Länge in Millisekunden"""
        if not audio_data or len(audio_data) < 44:  # WAV-Header
            return 0.0

        audio_bytes = len(audio_data) - 44
        samples = audio_bytes // 2  # 16-bit Audio
        return (samples / sample_rate) * 1000
        
    async def cleanup(self):
        """Cleanup Piper TTS Ressourcen"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)
        self.voice_cache.clear()
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
