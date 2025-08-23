"""Staged TTS Processor – planbasiert (Intro/Main), konfigurierbar"""

import asyncio
import time
import uuid
import base64
import logging
import re
COMBINING_RE = re.compile(r'[\u0300-\u036F]')
INTRO_MAX_CHARS = 160  # added by patch: begrenze Intro-Länge
INTRO_TIMEOUT_MS = 8000

logger = logging.getLogger(__name__)
import hashlib
from typing import List, Dict, Any, Optional
from ws_server.tts.text_sanitizer import sanitize_for_tts as sanitize_for_tts_strict
from dataclasses import dataclass
from collections import OrderedDict
from ws_server.metrics.collector import collector
from ws_server.tts.text_normalize import sanitize_for_tts as sanitize_basic

logger = logging.getLogger(__name__)


def _hardcore_sanitize_text(text: str) -> str:
    """Entfernt ALLE problematischen Zeichen für Piper TTS"""
    if not text:
        return text
    
    import unicodedata
    
    # Unicode normalisieren
    text = unicodedata.normalize("NFKC", text)
    
    # HARDCORE: Alle diakritischen Zeichen entfernen
    # Das ist der Grund für "Missing phoneme from id map: ̧"
    text = ''.join(
        char for char in unicodedata.normalize('NFD', text)
        if unicodedata.category(char) != 'Mn'  # Remove all marks (diakritika)
    )
    
    # Zusätzliche problematische Zeichen
    replacements = {
        chr(0x0327): '',      # Combining cedilla ̧ (Hauptproblem!)
        'ç': 'c',             # c mit Cedilla
        chr(0x201C): '"',     # Left double quote
        chr(0x201D): '"',     # Right double quote
        chr(0x2018): "'",     # Left single quote  
        chr(0x2019): "'",     # Right single quote
        chr(0x2014): '-',     # Em dash
        chr(0x2013): '-',     # En dash
        chr(0x2026): '...',   # Ellipsis
        chr(0x00A0): ' ',     # Non-breaking space
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    # Mehrfache Leerzeichen normalisieren
    text = ' '.join(text.split())
    
    return text


@dataclass
class TTSChunk:
    """Repräsentiert einen TTS-Chunk mit Metadaten"""
    sequence_id: str
    index: int
    total: int
    engine: str
    text: str
    audio_data: Optional[bytes]
    success: bool
    error_message: Optional[str] = None


@dataclass
class StagedTTSConfig:
    """Konfiguration für Staged TTS"""
    enabled: bool = True
    max_response_length: int = 500
    max_intro_length: int = 120
    chunk_timeout_seconds: int = 10
    max_chunks: int = 3
    enable_caching: bool = True
    cache_size: int = 256
    crossfade_duration_ms: int = 100



@dataclass
class StagedPlan:
    """Plan/Policy für Intro/Main – 'auto' wählt dynamisch."""
    intro_engine: str | None = "auto"   # 'auto'|'piper'|'zonos'|None
    main_engine:  str | None = "auto"   # 'auto'|'piper'|'zonos'|None
    fast_start:   bool = True           # Intro parallel, wenn vorhanden

def _env_override(name: str) -> str | None:
    import os
    val = os.getenv(name) or os.getenv(name.lower())
    if not val:
        return None
    v = val.strip().lower()
    return v if v in {"auto","piper","zonos","kokoro","none",""} else None


class StagedTTSProcessor:
    """
    Hauptklasse für Staged TTS Processing

    Implementiert das zweistufige System:
    - Stage A: Piper Intro (CPU, schnell)
    - Stage B: Zonos Hauptinhalt (GPU, hochwertig)
    """

    def __init__(self, tts_manager, config: StagedTTSConfig = None):
        self.plan = StagedPlan()
        self.tts_manager = tts_manager
        self.config = config or StagedTTSConfig()
        # LRU Cache for synthesized audio
        self._cache: "OrderedDict[str, bytes]" = OrderedDict()

        
    async def process_staged_tts(self, text: str, canonical_voice: str) -> List[TTSChunk]:
        """
        Verarbeite Text mit Staged TTS Approach.
        
        Args:
            text: Eingabetext
            
        Returns:
            Liste von TTSChunk-Objekten in der richtigen Reihenfolge
        """
        # Hard sanitization gate
        text = sanitize_for_tts_strict(text)
        # Vorab: aggressive Sanitization (kombinierende Zeichen raus)
        text = sanitize_basic(text)
        from .chunking import _limit_and_chunk, create_intro_chunk, optimize_for_prosody
        
        # Text optimieren und chunken
        optimized_text = optimize_for_prosody(text)
        chunks = _limit_and_chunk(optimized_text, self.config.max_response_length)
        
        if not chunks:
            logger.warning("Keine Text-Chunks generiert")
            return []
        
        # Intro und Hauptinhalt aufteilen
        intro_text, main_chunks = create_intro_chunk(chunks, self.config.max_intro_length)
        
        # Sequence ID generieren
        sequence_id = uuid.uuid4().hex[:8]

        # Plan bestimmen (konfigurierbar, ohne Hartverdrahtung)
        plan = self._resolve_plan(canonical_voice)
        
        # Tasks für parallele Verarbeitung erstellen
        tasks = []
        
        # Stage A: Piper Intro (sofort starten)
        if intro_text and plan.intro_engine:
            intro_task = asyncio.create_task(
                self._synthesize_chunk(
                    text=intro_text,
                    engine=plan.intro_engine,
                    sequence_id=sequence_id,
                    index=0,
                    total=1 + len(main_chunks),
                    voice=canonical_voice,
                )
            )
            tasks.append(intro_task)
        
                # Stage B: Main-Streaming (parallel verarbeiten)
        if plan.main_engine:
            for i, chunk_text in enumerate(main_chunks[: self.config.max_chunks - 1]):
                main_task = asyncio.create_task(
                    self._synthesize_chunk(
                        text=chunk_text,
                        engine=plan.main_engine,
                        sequence_id=sequence_id,
                        index=i + 1,
                        total=1 + len(main_chunks),
                        voice=canonical_voice,
                    )
                )
                tasks.append(main_task)
        else:
            logger.info("Keine Main-Engine verfügbar – nur Intro wird (falls vorhanden) gespielt.")
        
        completed_chunks = await asyncio.gather(*tasks, return_exceptions=True)

        # Sortiere Chunks nach Index
        valid_chunks = [chunk for chunk in completed_chunks if isinstance(chunk, TTSChunk)]
        valid_chunks.sort(key=lambda x: x.index)

        return valid_chunks
    
    async def _synthesize_chunk(self, text: str, engine: str, sequence_id: str,
                               index: int, total: int, voice: str) -> TTSChunk:
        """
        Synthetisiere einen einzelnen Text-Chunk.
        
        Args:
            text: Text für TTS
            engine: Engine-Name ("piper" oder "zonos")
            sequence_id: Sequenz-ID
            index: Chunk-Index
            total: Gesamtanzahl Chunks
            
        Returns:
            TTSChunk mit Ergebnis
        """
        try:
            # Cache key based on engine and text hash
            cache_key = f"{engine}:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"
            if self.config.enable_caching and cache_key in self._cache:
                logger.debug(f"Cache hit für {engine} chunk {index}")
                audio = self._cache.pop(cache_key)
                self._cache[cache_key] = audio
                return TTSChunk(
                    sequence_id=sequence_id,
                    index=index,
                    total=total,
                    engine=engine,
                    text=text,
                    audio_data=audio,
                    success=True
                )

            # TTS-Synthese mit Timeout
            start_time = time.time()
            try:
                text = COMBINING_RE.sub('', text)
                result = await asyncio.wait_for(
                    self.tts_manager.synthesize(text, engine=engine, voice=voice),
                    timeout=self.config.chunk_timeout_seconds,
                )
            except asyncio.TimeoutError:
                logger.warning(f"{engine.capitalize()} TTS Timeout für chunk {index}")
                collector.tts_sequence_timeout_total.labels(engine=engine).inc()
                return TTSChunk(
                    sequence_id=sequence_id,
                    index=index,
                    total=total,
                    engine=engine,
                    text=text,
                    audio_data=None,
                    success=False,
                    error_message="timeout"
                )

            processing_time = time.time() - start_time
            logger.debug(f"{engine.capitalize()} TTS chunk {index}: {processing_time:.2f}s")

            if result.success and result.audio_data:
                if self.config.enable_caching:
                    self._cache[cache_key] = result.audio_data
                    if len(self._cache) > self.config.cache_size:
                        self._cache.popitem(last=False)
                return TTSChunk(
                    sequence_id=sequence_id,
                    index=index,
                    total=total,
                    engine=engine,
                    text=text,
                    audio_data=result.audio_data,
                    success=True
                )
            logger.warning(f"{engine.capitalize()} TTS fehlgeschlagen für chunk {index}: {result.error_message}")
            return TTSChunk(
                sequence_id=sequence_id,
                index=index,
                total=total,
                engine=engine,
                text=text,
                audio_data=None,
                success=False,
                error_message=result.error_message
            )
                
        except Exception as e:
            logger.error(f"Fehler bei {engine} TTS chunk {index}: {e}")
            return TTSChunk(
                sequence_id=sequence_id,
                index=index,
                total=total,
                engine=engine,
                text=text,
                audio_data=None,
                success=False,
                error_message=str(e)
            )
    
    def create_chunk_message(self, chunk: TTSChunk) -> Dict[str, Any]:
        """Erstelle WebSocket-Message für TTS-Chunk."""
        audio_b64 = ""
        try:
            if chunk.audio_data:
                import base64
                audio_b64 = base64.b64encode(chunk.audio_data).decode("ascii")
        except Exception as e:
            logger.warning(
                "STAGED_TTS::encode_failed | seq=%s idx=%s err=%s",
                getattr(chunk, "sequence_id", None),
                getattr(chunk, "index", None),
                e,
            )

        # Metriken
        if chunk.success and chunk.audio_data:
            try:
                collector.tts_chunk_emitted_total.labels(engine=chunk.engine).inc()
                collector.audio_out_bytes_total.inc(len(chunk.audio_data))
            except Exception:
                pass

        msg = {
            "type": "tts_chunk",
            "sequence_id": chunk.sequence_id,
            "index": chunk.index,
            "total": chunk.total,
            "engine": chunk.engine,
            "text": chunk.text,
            "audio": f"data:audio/wav;base64,{audio_b64}" if audio_b64 else None,
            "success": chunk.success,
            "error": chunk.error_message,
            "timestamp": time.time(),
            "crossfade_ms": self.config.crossfade_duration_ms,
        }
        logger.debug(
            "STAGED_TTS::chunk_msg | seq=%s idx=%s/%s engine=%s audio=%s",
            chunk.sequence_id,
            chunk.index,
            chunk.total,
            chunk.engine,
            "yes" if audio_b64 else "no",
        )
        return msg
    def get_cache_stats(self) -> Dict[str, Any]:
        """Gib Cache-Statistiken zurück."""
        total_size = sum(len(data) for data in self._cache.values())





    def _engine_available_for_voice(self, engine: str, voice: str) -> bool:
        try:
            if hasattr(self.tts_manager, "engine_allowed_for_voice"):
                return bool(self.tts_manager.engine_allowed_for_voice(engine, voice))
            return engine in getattr(self.tts_manager, "engines", {})
        except Exception:
            return False

    def _resolve_plan(self, canonical_voice: str) -> StagedPlan:
        """
        Priorität:
        1) ENV: STAGED_TTS_INTRO_ENGINE / STAGED_TTS_MAIN_ENGINE
        2) (optional) config-Datei (nicht zwingend)
        3) 'auto': Intro bevorzugt Piper (fast), Main bevorzugt Zonos (Qualität)
        """
        intro = _env_override("STAGED_TTS_INTRO_ENGINE")
        main  = _env_override("STAGED_TTS_MAIN_ENGINE")

        try:
            intro = intro or globals().get("INTRO_ENGINE", None)
            main  = main  or globals().get("MAIN_ENGINE", None)
        except Exception:
            pass

        if intro in ("none",""): intro = None
        if main  in ("none",""): main  = None

        plan = StagedPlan(intro_engine=intro or "auto",
                          main_engine= main  or "auto",
                          fast_start=True)

        def pick_intro():
            if self._engine_available_for_voice("piper", canonical_voice):
                return "piper"
            return None

        def pick_main():
            if self._engine_available_for_voice("zonos", canonical_voice):
                return "zonos"
            if self._engine_available_for_voice("piper", canonical_voice):
                return "piper"
            return None

        if plan.intro_engine == "auto":
            plan.intro_engine = pick_intro()
        if plan.main_engine == "auto":
            plan.main_engine = pick_main()

        logger.info("STAGED_TTS::plan | intro=%s | main=%s | voice=%s",
                    plan.intro_engine, plan.main_engine, canonical_voice)
        return plan
# ---- added by patch: verbose staged-tts logger ----
def _staged_log(evt: str, **kw):
    try:
        parts = [f"STAGED_TTS::{evt}"]
        for k,v in kw.items():
            if k in ("text","chunk_audio"):
                # nicht den gesamten Text/Audios ausgeben
                if isinstance(v,str):
                    parts.append(f"{k}len={len(v)}")
                else:
                    parts.append(f"{k}type={type(v).__name__}")
            else:
                parts.append(f"{k}={v}")
        logger.info(" | ".join(parts))
    except Exception as e:
        logger.debug("staged_log error: %s", e)


# added by patch: PHASE_MAIN_ENGINE_ENFORCE
def _enforce_main_engine(engine_name: str | None) -> str:
    # fallback auf gesetzten MAIN_ENGINE
    return (engine_name or "").strip() or globals().get("MAIN_ENGINE", "zonos")

    def create_chunk_message(self, chunk: 'TTSChunk') -> Dict[str, Any]:
        """Erstelle WebSocket-Message für TTS-Chunk."""
        audio_b64 = ""
        try:
            if chunk.audio_data:
                audio_b64 = base64.b64encode(chunk.audio_data).decode("ascii")
        except Exception as e:
            logger.warning(
                "STAGED_TTS::encode_failed | seq=%s idx=%s err=%s",
                getattr(chunk, "sequence_id", None),
                getattr(chunk, "index", None),
                e,
            )
    
        # Metriken
        if chunk.success and chunk.audio_data:
            try:
                collector.tts_chunk_emitted_total.labels(engine=chunk.engine).inc()
                collector.audio_out_bytes_total.inc(len(chunk.audio_data))
            except Exception:
                pass
    
        msg = {
            "type": "tts_chunk",
            "sequence_id": chunk.sequence_id,
            "index": chunk.index,
            "total": chunk.total,
            "engine": chunk.engine,
            "text": chunk.text,
            "audio": f"data:audio/wav;base64,{audio_b64}" if audio_b64 else None,
            "success": chunk.success,
            "error": chunk.error_message,
            "timestamp": time.time(),
            "crossfade_ms": self.config.crossfade_duration_ms,
        }
        logger.debug(
            "STAGED_TTS::chunk_msg | seq=%s idx=%s/%s engine=%s audio=%s",
            chunk.sequence_id,
            chunk.index,
            chunk.total,
            chunk.engine,
            "yes" if audio_b64 else "no",
        )
        return msg

    def create_sequence_end_message(self, sequence_id: str) -> Dict[str, Any]:
        """Erstelle Sequenz-Ende-Message."""
        msg = {
            "type": "tts_sequence_end",
            "sequence_id": sequence_id,
            "timestamp": time.time(),
        }
        logger.debug("STAGED_TTS::sequence_end | seq=%s", sequence_id)
        return msg

    def get_cache_stats(self) -> Dict[str, Any]:
        """Gib Cache-Statistiken zurück."""
        total_size = sum(len(data) for data in self._cache.values())

    def create_chunk_message(self, chunk: 'TTSChunk') -> Dict[str, Any]:
        """Erstelle WebSocket-Message für TTS-Chunk."""
        audio_b64 = ""
        try:
            if chunk.audio_data:
                audio_b64 = base64.b64encode(chunk.audio_data).decode("ascii")
        except Exception as e:
            logger.warning(
                "STAGED_TTS::encode_failed | seq=%s idx=%s err=%s",
                getattr(chunk, "sequence_id", None),
                getattr(chunk, "index", None),
                e,
            )
    
        # Metriken
        if chunk.success and chunk.audio_data:
            try:
                collector.tts_chunk_emitted_total.labels(engine=chunk.engine).inc()
                collector.audio_out_bytes_total.inc(len(chunk.audio_data))
            except Exception:
                pass
    
        msg = {
            "type": "tts_chunk",
            "sequence_id": chunk.sequence_id,
            "index": chunk.index,
            "total": chunk.total,
            "engine": chunk.engine,
            "text": chunk.text,
            "audio": f"data:audio/wav;base64,{audio_b64}" if audio_b64 else None,
            "success": chunk.success,
            "error": chunk.error_message,
            "timestamp": time.time(),
            "crossfade_ms": self.config.crossfade_duration_ms,
        }
        logger.debug(
            "STAGED_TTS::chunk_msg | seq=%s idx=%s/%s engine=%s audio=%s",
            chunk.sequence_id,
            chunk.index,
            chunk.total,
            chunk.engine,
            "yes" if audio_b64 else "no",
        )
        return msg

    def create_sequence_end_message(self, sequence_id: str) -> Dict[str, Any]:
        """Erstelle Sequenz-Ende-Message."""
        msg = {
            "type": "tts_sequence_end",
            "sequence_id": sequence_id,
            "timestamp": time.time(),
        }
        logger.debug("STAGED_TTS::sequence_end | seq=%s", sequence_id)
        return msg

    def get_cache_stats(self) -> Dict[str, Any]:
        """Gib Cache-Statistiken zurück."""
        total_size = sum(len(data) for data in self._cache.values())
        return {
            "entries": len(self._cache),
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
        }

    def create_sequence_end_message(self, sequence_id: str) -> Dict[str, Any]:
        """Erstelle Sequenz-Ende-Message."""
        msg = {
            "type": "tts_sequence_end",
            "sequence_id": sequence_id,
            "timestamp": time.time(),
        }
        logger.debug("STAGED_TTS::sequence_end | seq=%s", sequence_id)
        return msg


# --- staged_tts safety patch: ensure create_sequence_end_message exists ---
def _staged__create_sequence_end_message(self, sequence_id: str) -> dict:
    msg = {
        "type": "tts_sequence_end",
        "sequence_id": sequence_id,
        "timestamp": time.time(),
    }
    logger.debug("STAGED_TTS::sequence_end | seq=%s", sequence_id)
    return msg

try:
    _has = hasattr(StagedTTSProcessor, "create_sequence_end_message")
except Exception:
    _has = False
if not _has:
    try:
        StagedTTSProcessor.create_sequence_end_message = _staged__create_sequence_end_message  # type: ignore[attr-defined]
        logger.info("STAGED_TTS::patch | create_sequence_end_message attached at runtime")
    except Exception as _e:
        logger.error("STAGED_TTS::patch_failed | %s", _e)

