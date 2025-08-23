#!/usr/bin/env python3
"""
Erweiterte Staged TTS Konfiguration
Robuste Timeout-Behandlung und Fallback-Mechanismen
"""

import os
import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Union
from enum import Enum

logger = logging.getLogger(__name__)

class TTSEngine(Enum):
    PIPER = "piper"
    ZONOS = "zonos"
    KOKORO = "kokoro"
    AUTO = "auto"

@dataclass
class StagedTTSConfig:
    """Konfiguration für Staged TTS System"""
    
    # Staging aktiviert?
    enabled: bool = True
    
    # Engine-Zuordnung
    intro_engine: TTSEngine = TTSEngine.PIPER
    main_engine: TTSEngine = TTSEngine.ZONOS
    fallback_engine: TTSEngine = TTSEngine.ZONOS
    
    # Text-Splitting
    max_response_length: int = 800
    max_intro_length: int = 150
    chunk_size_min: int = 80
    chunk_size_max: int = 200
    chunk_overlap: int = 10
    
    # Timeout-Einstellungen (in Sekunden)
    intro_timeout: float = 8.0      # Reduziert von 10s
    chunk_timeout: float = 12.0     # Pro Chunk
    total_timeout: float = 45.0     # Gesamt-Timeout
    
    # Retry-Verhalten
    max_retries: int = 2
    retry_delay: float = 0.5
    
    # Caching
    enable_caching: bool = True
    cache_size: int = 100
    cache_ttl: int = 3600  # 1 Stunde
    
    # Debug/Monitoring
    debug_mode: bool = False
    log_performance: bool = True
    
    # Fallback-Strategien
    fallback_on_timeout: bool = True
    fallback_on_error: bool = True
    allow_partial_audio: bool = True
    
    # Text-Bereinigung
    sanitize_text: bool = True
    strict_ascii_mode: bool = False  # Nur ASCII für problematische Engines
    
    @classmethod
    def from_env(cls) -> 'StagedTTSConfig':
        """Erstellt Konfiguration aus Umgebungsvariablen"""
        
        def get_bool(key: str, default: bool) -> bool:
            return os.getenv(key, str(default)).lower() in ('true', '1', 'yes', 'on')
        
        def get_float(key: str, default: float) -> float:
            try:
                return float(os.getenv(key, str(default)))
            except ValueError:
                return default
        
        def get_int(key: str, default: int) -> int:
            try:
                return int(os.getenv(key, str(default)))
            except ValueError:
                return default
        
        def get_engine(key: str, default: TTSEngine) -> TTSEngine:
            value = os.getenv(key, default.value).lower()
            try:
                return TTSEngine(value)
            except ValueError:
                return default
        
        return cls(
            enabled=get_bool('STAGED_TTS_ENABLED', True),
            intro_engine=get_engine('STAGED_TTS_INTRO_ENGINE', TTSEngine.PIPER),
            main_engine=get_engine('STAGED_TTS_MAIN_ENGINE', TTSEngine.ZONOS),
            fallback_engine=get_engine('STAGED_TTS_FALLBACK_ENGINE', TTSEngine.ZONOS),
            
            max_response_length=get_int('STAGED_TTS_MAX_RESPONSE_LENGTH', 800),
            max_intro_length=get_int('STAGED_TTS_MAX_INTRO_LENGTH', 150),
            chunk_size_min=get_int('STAGED_TTS_CHUNK_SIZE_MIN', 80),
            chunk_size_max=get_int('STAGED_TTS_CHUNK_SIZE_MAX', 200),
            
            intro_timeout=get_float('STAGED_TTS_INTRO_TIMEOUT', 8.0),
            chunk_timeout=get_float('STAGED_TTS_CHUNK_TIMEOUT', 12.0),
            total_timeout=get_float('STAGED_TTS_TOTAL_TIMEOUT', 45.0),
            
            max_retries=get_int('STAGED_TTS_MAX_RETRIES', 2),
            retry_delay=get_float('STAGED_TTS_RETRY_DELAY', 0.5),
            
            enable_caching=get_bool('STAGED_TTS_ENABLE_CACHING', True),
            cache_size=get_int('STAGED_TTS_CACHE_SIZE', 100),
            cache_ttl=get_int('STAGED_TTS_CACHE_TTL', 3600),
            
            debug_mode=get_bool('STAGED_TTS_DEBUG', False),
            log_performance=get_bool('STAGED_TTS_LOG_PERFORMANCE', True),
            
            fallback_on_timeout=get_bool('STAGED_TTS_FALLBACK_ON_TIMEOUT', True),
            fallback_on_error=get_bool('STAGED_TTS_FALLBACK_ON_ERROR', True),
            allow_partial_audio=get_bool('STAGED_TTS_ALLOW_PARTIAL', True),
            
            sanitize_text=get_bool('STAGED_TTS_SANITIZE_TEXT', True),
            strict_ascii_mode=get_bool('STAGED_TTS_STRICT_ASCII', False),
        )
    
    def update_from_dict(self, updates: Dict) -> None:
        """Aktualisiert Konfiguration zur Laufzeit"""
        for key, value in updates.items():
            if hasattr(self, key):
                # Engine-Namen konvertieren
                if key.endswith('_engine') and isinstance(value, str):
                    try:
                        value = TTSEngine(value.lower())
                    except ValueError:
                        continue
                
                setattr(self, key, value)
                if self.debug_mode:
                    logger.debug(f"Updated staged TTS config: {key} = {value}")

@dataclass
class TTSChunkTask:
    """Einzelne TTS-Aufgabe in der Staging-Pipeline"""
    
    chunk_id: str
    sequence_id: str
    text: str
    engine: TTSEngine
    index: int
    total_chunks: int
    
    # Status
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    failed_at: Optional[float] = None
    
    # Ergebnis
    audio_data: Optional[bytes] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    
    @property
    def is_completed(self) -> bool:
        return self.completed_at is not None
    
    @property
    def is_failed(self) -> bool:
        return self.failed_at is not None
    
    @property
    def processing_time(self) -> Optional[float]:
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None
    
    def start(self) -> None:
        self.started_at = time.time()
    
    def complete(self, audio_data: bytes) -> None:
        self.completed_at = time.time()
        self.audio_data = audio_data
    
    def fail(self, error_message: str) -> None:
        self.failed_at = time.time()
        self.error_message = error_message

class StagedTTSManager:
    """Manager für Staged TTS mit robusten Timeout- und Fallback-Mechanismen"""
    
    def __init__(self, config: Optional[StagedTTSConfig] = None):
        self.config = config or StagedTTSConfig.from_env()
        self.active_sequences: Dict[str, List[TTSChunkTask]] = {}
        self.performance_stats = {
            'total_sequences': 0,
            'successful_sequences': 0,
            'failed_sequences': 0,
            'fallback_used': 0,
            'avg_processing_time': 0.0,
            'piper_timeouts': 0,
            'zonos_timeouts': 0,
        }
        
        if self.config.debug_mode:
            logger.info(f"🎭 Staged TTS Manager initialized with config: {self.config}")
    
    async def process_text_staged(self, text: str, sequence_id: str) -> List[TTSChunkTask]:
        """Verarbeitet Text mit Staged TTS"""
        start_time = time.time()
        
        try:
            # Text bereinigen falls aktiviert
            if self.config.sanitize_text:
                text = self._sanitize_text(text)
            
            # Zu lang? Fallback zu single engine
            if len(text) > self.config.max_response_length:
                logger.info(f"Text too long ({len(text)}), using fallback engine only")
                return await self._process_with_fallback(text, sequence_id)
            
            # Text in Chunks aufteilen
            chunks = self._split_text_for_staging(text)
            
            if not chunks:
                return []
            
            # Tasks erstellen
            tasks = []
            intro_task = None
            
            for i, chunk_text in enumerate(chunks):
                engine = self.config.intro_engine if i == 0 else self.config.main_engine
                task = TTSChunkTask(
                    chunk_id=f"{sequence_id}_chunk_{i}",
                    sequence_id=sequence_id,
                    text=chunk_text,
                    engine=engine,
                    index=i,
                    total_chunks=len(chunks)
                )
                tasks.append(task)
                if i == 0:
                    intro_task = task
            
            self.active_sequences[sequence_id] = tasks
            
            # Intro mit speziellem Timeout starten
            if intro_task:
                await self._process_task_with_timeout(
                    intro_task, 
                    timeout=self.config.intro_timeout,
                    is_intro=True
                )
            
            # Restliche Chunks parallel verarbeiten
            remaining_tasks = tasks[1:] if len(tasks) > 1 else []
            if remaining_tasks:
                await self._process_tasks_parallel(remaining_tasks)
            
            # Performance-Tracking
            processing_time = time.time() - start_time
            self._update_performance_stats(tasks, processing_time)
            
            return tasks
            
        except Exception as e:
            logger.error(f"Staged TTS processing failed: {e}")
            return await self._process_with_fallback(text, sequence_id)
    
    def _sanitize_text(self, text: str) -> str:
        """Bereinigt Text für TTS-Verarbeitung"""
        # Import hier um zirkuläre Abhängigkeiten zu vermeiden
        try:
            from .text_sanitizer import sanitize_for_tts_strict
            return sanitize_for_tts_strict(text)
        except ImportError:
            # Fallback: Einfache Bereinigung
            import re
            import unicodedata
            
            # Unicode normalisieren
            text = unicodedata.normalize('NFKC', text)
            
            # Problematische Zeichen ersetzen
            replacements = {
                'ç': 'c', '̧': '', '"': '"', '"': '"',
                '—': '-', '–': '-', '…': '...'
            }
            
            for old, new in replacements.items():
                text = text.replace(old, new)
            
            # Multiple Leerzeichen normalisieren
            text = re.sub(r'\s+', ' ', text)
            
            return text.strip()
    
    def _split_text_for_staging(self, text: str) -> List[str]:
        """Teilt Text für Staged TTS auf"""
        if len(text) <= self.config.max_intro_length:
            return [text]  # Kurzer Text - kein Splitting nötig
        
        chunks = []
        
        # Intro-Chunk (erste N Zeichen)
        intro_text = text[:self.config.max_intro_length]
        
        # Am Wortende trennen
        if len(text) > self.config.max_intro_length:
            last_space = intro_text.rfind(' ')
            if last_space > self.config.max_intro_length * 0.7:  # Mindestens 70% der gewünschten Länge
                intro_text = intro_text[:last_space]
        
        chunks.append(intro_text)
        
        # Rest-Text in weitere Chunks
        remaining_text = text[len(intro_text):].strip()
        
        while remaining_text:
            chunk_size = min(self.config.chunk_size_max, len(remaining_text))
            chunk = remaining_text[:chunk_size]
            
            # Am Satzende oder Wortende trennen
            if len(remaining_text) > chunk_size:
                sentence_end = max(
                    chunk.rfind('.'), chunk.rfind('!'), 
                    chunk.rfind('?'), chunk.rfind(';')
                )
                if sentence_end > chunk_size * 0.6:
                    chunk = chunk[:sentence_end + 1]
                else:
                    word_end = chunk.rfind(' ')
                    if word_end > chunk_size * 0.7:
                        chunk = chunk[:word_end]
            
            chunks.append(chunk.strip())
            remaining_text = remaining_text[len(chunk):].strip()
            
            # Sicherheit gegen Endlosschleife
            if len(chunks) > 10:  # Max 10 Chunks
                if remaining_text:
                    chunks[-1] += ' ' + remaining_text
                break
        
        return [c for c in chunks if c.strip()]  # Leere Chunks entfernen
    
    async def _process_task_with_timeout(self, task: TTSChunkTask, timeout: float, is_intro: bool = False) -> None:
        """Verarbeitet einzelne Task mit Timeout"""
        task.start()
        
        try:
            # Hier würde die eigentliche TTS-Engine aufgerufen werden
            # Für diese Implementierung simulieren wir das
            await asyncio.sleep(0.1)  # Simulierte Verarbeitung
            task.complete(b'dummy_audio_data')
            
            if self.config.debug_mode:
                engine_name = task.engine.value.upper()
                timing_info = f"in {task.processing_time:.2f}s" if task.processing_time else ""
                logger.info(f"✅ {engine_name} chunk {task.index}/{task.total_chunks-1} completed {timing_info}")
                
        except asyncio.TimeoutError:
            task.fail("Timeout")
            self.performance_stats[f'{task.engine.value}_timeouts'] += 1
            
            logger.warning(f"⏰ {task.engine.value.upper()} timeout for chunk {task.index} after {timeout}s")
            
            if is_intro and self.config.fallback_on_timeout:
                logger.info("🔄 Intro failed, switching to fallback engine for whole sequence")
                # Hier würde Fallback-Logik implementiert werden
                
        except Exception as e:
            task.fail(str(e))
            logger.error(f"❌ {task.engine.value.upper()} chunk {task.index} failed: {e}")
    
    async def _process_tasks_parallel(self, tasks: List[TTSChunkTask]) -> None:
        """Verarbeitet Tasks parallel mit individuellen Timeouts"""
        if not tasks:
            return
        
        # Tasks mit Timeout wrappen
        timeout_tasks = [
            asyncio.wait_for(
                self._process_task_with_timeout(task, self.config.chunk_timeout),
                timeout=self.config.chunk_timeout
            )
            for task in tasks
        ]
        
        # Alle parallel ausführen
        results = await asyncio.gather(*timeout_tasks, return_exceptions=True)
        
        # Fehler loggen
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                tasks[i].fail(str(result))
    
    async def _process_with_fallback(self, text: str, sequence_id: str) -> List[TTSChunkTask]:
        """Fallback: Single-Engine Verarbeitung"""
        self.performance_stats['fallback_used'] += 1
        
        task = TTSChunkTask(
            chunk_id=f"{sequence_id}_fallback",
            sequence_id=sequence_id,
            text=text,
            engine=self.config.fallback_engine,
            index=0,
            total_chunks=1
        )
        
        await self._process_task_with_timeout(task, self.config.total_timeout)
        return [task]
    
    def _update_performance_stats(self, tasks: List[TTSChunkTask], processing_time: float) -> None:
        """Aktualisiert Performance-Statistiken"""
        self.performance_stats['total_sequences'] += 1
        
        if all(task.is_completed for task in tasks):
            self.performance_stats['successful_sequences'] += 1
        else:
            self.performance_stats['failed_sequences'] += 1
        
        # Durchschnittliche Verarbeitungszeit aktualisieren
        current_avg = self.performance_stats['avg_processing_time']
        total_seqs = self.performance_stats['total_sequences']
        self.performance_stats['avg_processing_time'] = (
            (current_avg * (total_seqs - 1) + processing_time) / total_seqs
        )
        
        if self.config.log_performance:
            success_rate = (
                self.performance_stats['successful_sequences'] / 
                self.performance_stats['total_sequences'] * 100
            )
            logger.info(
                f"📊 Staged TTS Stats: {success_rate:.1f}% success, "
                f"avg {self.performance_stats['avg_processing_time']:.2f}s, "
                f"fallbacks: {self.performance_stats['fallback_used']}"
            )
    
    def get_stats(self) -> Dict:
        """Gibt aktuelle Performance-Statistiken zurück"""
        return {
            **self.performance_stats,
            'config': {
                'intro_timeout': self.config.intro_timeout,
                'chunk_timeout': self.config.chunk_timeout,
                'max_intro_length': self.config.max_intro_length,
                'fallback_enabled': self.config.fallback_on_timeout,
                'sanitization_enabled': self.config.sanitize_text
            }
        }

# Factory-Funktion für globale Instanz
_staged_tts_manager: Optional[StagedTTSManager] = None

def get_staged_tts_manager() -> StagedTTSManager:
    """Singleton-Pattern für StagedTTSManager"""
    global _staged_tts_manager
    if _staged_tts_manager is None:
        _staged_tts_manager = StagedTTSManager()
    return _staged_tts_manager