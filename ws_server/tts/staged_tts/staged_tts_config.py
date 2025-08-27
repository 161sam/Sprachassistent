# -*- coding: utf-8 -*-
"""
Staged TTS Konfiguration & einfacher Manager (kompatibel zu Adapter/Processor).
- ENV-Overrides via StagedTTSConfig.from_env()
- Minimaler StagedTTSManager (async Platzhalter-Implementierung), damit Imports funktionieren
"""
from __future__ import annotations
import os, time, logging, asyncio, unicodedata, re
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)

class TTSEngine(Enum):
    PIPER = "piper"
    ZONOS = "zonos"
    KOKORO = "kokoro"
    AUTO = "auto"

@dataclass
class StagedTTSConfig:
    enabled: bool = True
    intro_engine: TTSEngine = TTSEngine.PIPER
    main_engine: TTSEngine = TTSEngine.ZONOS
    fallback_engine: TTSEngine = TTSEngine.ZONOS
    max_response_length: int = 800
    max_intro_length: int = 150
    chunk_size_min: int = 80
    chunk_size_max: int = 200
    chunk_overlap: int = 10
    intro_timeout: float = 8.0
    chunk_timeout: float = 12.0
    total_timeout: float = 45.0
    max_retries: int = 2
    retry_delay: float = 0.5
    enable_caching: bool = True
    cache_size: int = 100
    cache_ttl: int = 3600
    debug_mode: bool = False
    log_performance: bool = True
    fallback_on_timeout: bool = True
    fallback_on_error: bool = True
    allow_partial_audio: bool = True
    sanitize_text: bool = True
    strict_ascii_mode: bool = False

    @classmethod
    def from_env(cls) -> 'StagedTTSConfig':
        def b(key, default): return os.getenv(key, str(default)).lower() in ("1","true","yes","on")
        def f(key, default):
            try: return float(os.getenv(key, str(default)))
            except ValueError: return default
        def i(key, default):
            try: return int(os.getenv(key, str(default)))
            except ValueError: return default
        def eng(key, default):
            val = os.getenv(key, default.value).lower()
            try: return type(default)(val)
            except ValueError: return default
        return cls(
            enabled=b('STAGED_TTS_ENABLED', True),
            intro_engine=eng('STAGED_TTS_INTRO_ENGINE', cls.intro_engine),
            main_engine=eng('STAGED_TTS_MAIN_ENGINE', cls.main_engine),
            fallback_engine=eng('STAGED_TTS_FALLBACK_ENGINE', cls.fallback_engine),
            max_response_length=i('STAGED_TTS_MAX_RESPONSE_LENGTH', 800),
            max_intro_length=i('STAGED_TTS_MAX_INTRO_LENGTH', 150),
            chunk_size_min=i('STAGED_TTS_CHUNK_SIZE_MIN', 80),
            chunk_size_max=i('STAGED_TTS_CHUNK_SIZE_MAX', 200),
            intro_timeout=f('STAGED_TTS_INTRO_TIMEOUT', 8.0),
            chunk_timeout=f('STAGED_TTS_CHUNK_TIMEOUT', 12.0),
            total_timeout=f('STAGED_TTS_TOTAL_TIMEOUT', 45.0),
            max_retries=i('STAGED_TTS_MAX_RETRIES', 2),
            retry_delay=f('STAGED_TTS_RETRY_DELAY', 0.5),
            enable_caching=b('STAGED_TTS_ENABLE_CACHING', True),
            cache_size=i('STAGED_TTS_CACHE_SIZE', 100),
            cache_ttl=i('STAGED_TTS_CACHE_TTL', 3600),
            debug_mode=b('STAGED_TTS_DEBUG', False),
            log_performance=b('STAGED_TTS_LOG_PERFORMANCE', True),
            fallback_on_timeout=b('STAGED_TTS_FALLBACK_ON_TIMEOUT', True),
            fallback_on_error=b('STAGED_TTS_FALLBACK_ON_ERROR', True),
            allow_partial_audio=b('STAGED_TTS_ALLOW_PARTIAL', True),
            sanitize_text=b('STAGED_TTS_SANITIZE_TEXT', True),
            strict_ascii_mode=b('STAGED_TTS_STRICT_ASCII', False),
        )

@dataclass
class TTSChunkTask:
    chunk_id: str
    sequence_id: str
    text: str
    engine: TTSEngine
    index: int
    total_chunks: int
    started_at: float | None = None
    completed_at: float | None = None
    failed_at: float | None = None
    audio_data: bytes | None = None
    error_message: str | None = None
    retry_count: int = 0
    @property
    def is_completed(self): return self.completed_at is not None
    @property
    def is_failed(self): return self.failed_at is not None
    @property
    def processing_time(self):
        return (self.completed_at - self.started_at) if (self.started_at and self.completed_at) else None
    def start(self): self.started_at = time.time()
    def complete(self, audio_data: bytes): self.completed_at = time.time(); self.audio_data = audio_data
    def fail(self, error_message: str): self.failed_at = time.time(); self.error_message = error_message

class StagedTTSManager:
    def __init__(self, config: StagedTTSConfig | None = None):
        self.config = config or StagedTTSConfig.from_env()
        self.active_sequences: Dict[str, List[TTSChunkTask]] = {}
        self.performance_stats = {'total_sequences':0,'successful_sequences':0,'failed_sequences':0,'fallback_used':0,'avg_processing_time':0.0,'piper_timeouts':0,'zonos_timeouts':0}
    async def process_text_staged(self, text: str, sequence_id: str) -> List[TTSChunkTask]:
        # Minimaler Platzhalter – die eigentliche Audiogenerierung passiert im Adapter/Engines.
        t = TTSChunkTask(f"{sequence_id}_intro", sequence_id, text, self.config.intro_engine, 0, 1)
        t.start(); await asyncio.sleep(0); t.complete(b""); return [t]

_staged_tts_manager = None
def get_staged_tts_manager():
    global _staged_tts_manager
    if _staged_tts_manager is None:
        _staged_tts_manager = StagedTTSManager()
    return _staged_tts_manager
