"""
Staged TTS Processor für parallele Piper + Zonos Verarbeitung
"""

import asyncio
import time
import uuid
import base64
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


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


class StagedTTSProcessor:
    """
    Hauptklasse für Staged TTS Processing
    
    Implementiert das zweistufige System:
    - Stage A: Piper Intro (CPU, schnell)
    - Stage B: Zonos Hauptinhalt (GPU, hochwertig)
    """
    
    def __init__(self, tts_manager, config: StagedTTSConfig = None):
        self.tts_manager = tts_manager
        self.config = config or StagedTTSConfig()
        self._cache: Dict[str, bytes] = {}
        
    async def process_staged_tts(self, text: str) -> List[TTSChunk]:
        """
        Verarbeite Text mit Staged TTS Approach.
        
        Args:
            text: Eingabetext
            
        Returns:
            Liste von TTSChunk-Objekten in der richtigen Reihenfolge
        """
        from .chunking import limit_and_chunk, create_intro_chunk, optimize_for_prosody
        
        # Text optimieren und chunken
        optimized_text = optimize_for_prosody(text)
        chunks = limit_and_chunk(optimized_text, self.config.max_response_length)
        
        if not chunks:
            logger.warning("Keine Text-Chunks generiert")
            return []
        
        # Intro und Hauptinhalt aufteilen
        intro_text, main_chunks = create_intro_chunk(chunks, self.config.max_intro_length)
        
        # Sequence ID generieren
        sequence_id = uuid.uuid4().hex[:8]
        
        # Tasks für parallele Verarbeitung erstellen
        tasks = []
        result_chunks = []
        
        # Stage A: Piper Intro (sofort starten)
        if intro_text:
            intro_task = asyncio.create_task(
                self._synthesize_chunk(
                    text=intro_text,
                    engine="piper",
                    sequence_id=sequence_id,
                    index=0,
                    total=1 + len(main_chunks)
                )
            )
            tasks.append(intro_task)
        
        # Stage B: Zonos Hauptinhalt (parallel verarbeiten)
        for i, chunk_text in enumerate(main_chunks[:self.config.max_chunks - 1]):
            zonos_task = asyncio.create_task(
                self._synthesize_chunk(
                    text=chunk_text,
                    engine="zonos",
                    sequence_id=sequence_id,
                    index=i + 1,
                    total=1 + len(main_chunks)
                )
            )
            tasks.append(zonos_task)
        
        # Warte auf alle Tasks mit Timeout
        try:
            completed_chunks = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.config.chunk_timeout_seconds * len(tasks)
            )
            
            # Sortiere Chunks nach Index
            valid_chunks = [chunk for chunk in completed_chunks 
                          if isinstance(chunk, TTSChunk)]
            valid_chunks.sort(key=lambda x: x.index)
            
            return valid_chunks
            
        except asyncio.TimeoutError:
            logger.warning(f"Staged TTS timeout nach {self.config.chunk_timeout_seconds}s")
            # Versuche wenigstens das Intro zurückzugeben
            if tasks:
                try:
                    intro_result = await asyncio.wait_for(tasks[0], timeout=1.0)
                    if isinstance(intro_result, TTSChunk):
                        return [intro_result]
                except asyncio.TimeoutError:
                    pass
            return []
    
    async def _synthesize_chunk(self, text: str, engine: str, sequence_id: str, 
                               index: int, total: int) -> TTSChunk:
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
            # Cache-Check
            cache_key = f"{engine}:{hash(text)}"
            if self.config.enable_caching and cache_key in self._cache:
                logger.debug(f"Cache hit für {engine} chunk {index}")
                return TTSChunk(
                    sequence_id=sequence_id,
                    index=index,
                    total=total,
                    engine=engine,
                    text=text,
                    audio_data=self._cache[cache_key],
                    success=True
                )
            
            # TTS-Synthese
            start_time = time.time()
            result = await self.tts_manager.synthesize(text, engine=engine)
            processing_time = time.time() - start_time
            
            logger.debug(f"{engine.capitalize()} TTS chunk {index}: {processing_time:.2f}s")
            
            if result.success and result.audio_data:
                # In Cache speichern
                if self.config.enable_caching:
                    self._cache[cache_key] = result.audio_data
                
                return TTSChunk(
                    sequence_id=sequence_id,
                    index=index,
                    total=total,
                    engine=engine,
                    text=text,
                    audio_data=result.audio_data,
                    success=True
                )
            else:
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
        """
        Erstelle WebSocket-Message für TTS-Chunk.
        
        Args:
            chunk: TTSChunk-Objekt
            
        Returns:
            WebSocket-Message Dictionary
        """
        audio_b64 = None
        if chunk.audio_data:
            audio_b64 = base64.b64encode(chunk.audio_data).decode("utf-8")
        
        return {
            "type": "tts_chunk",
            "sequence_id": chunk.sequence_id,
            "index": chunk.index,
            "total": chunk.total,
            "engine": chunk.engine,
            "text": chunk.text,
            "audio": f"data:audio/wav;base64,{audio_b64}" if audio_b64 else None,
            "success": chunk.success,
            "error": chunk.error_message,
            "timestamp": time.time()
        }
    
    def create_sequence_end_message(self, sequence_id: str) -> Dict[str, Any]:
        """
        Erstelle Sequenz-Ende-Message.
        
        Args:
            sequence_id: Sequenz-ID
            
        Returns:
            WebSocket-Message Dictionary
        """
        return {
            "type": "tts_sequence_end",
            "sequence_id": sequence_id,
            "timestamp": time.time()
        }
    
    def clear_cache(self):
        """Leere den TTS-Cache."""
        self._cache.clear()
        logger.info("TTS-Cache geleert")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Gib Cache-Statistiken zurück."""
        total_size = sum(len(data) for data in self._cache.values())
        return {
            "entries": len(self._cache),
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024)
        }
