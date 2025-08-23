"""Staged TTS Processor – intro via Piper, main via configurable engine."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import time
import uuid
from dataclasses import dataclass
from collections import OrderedDict
from typing import Any, Dict, List, Optional

from ws_server.metrics.collector import collector
from ws_server.tts.text_sanitizer import sanitize_for_tts_strict, pre_clean_for_piper
from ws_server.tts.text_normalize import sanitize_for_tts as sanitize_basic

logger = logging.getLogger(__name__)


@dataclass
class TTSChunk:
    """Represents a synthesized chunk with meta data."""
    sequence_id: str
    index: int
    total: int
    engine: str
    text: str
    audio_data: Optional[bytes]
    success: bool
    sample_rate: int
    error_message: Optional[str] = None


@dataclass
class StagedTTSConfig:
    enabled: bool = True
    max_response_length: int = 500
    max_intro_length: int = 120
    intro_timeout_seconds: int = 5
    chunk_timeout_seconds: int = 10
    max_chunks: int = 3
    enable_caching: bool = True
    cache_size: int = 256
    crossfade_duration_ms: int = 100

    @classmethod
    def from_env(cls) -> "StagedTTSConfig":
        import os
        cfg = cls()
        val = os.getenv("STAGED_TTS_CROSSFADE_MS")
        if val:
            try:
                cfg.crossfade_duration_ms = int(val)
            except ValueError:
                logger.warning("Ungültiger Wert für STAGED_TTS_CROSSFADE_MS: %s", val)
        val = os.getenv("STAGED_TTS_MAX_INTRO_LENGTH")
        if val:
            try:
                cfg.max_intro_length = int(val)
            except ValueError:
                logger.warning("Ungültiger Wert für STAGED_TTS_MAX_INTRO_LENGTH: %s", val)
        val = os.getenv("STAGED_TTS_INTRO_TIMEOUT")
        if val:
            try:
                cfg.intro_timeout_seconds = int(val)
            except ValueError:
                logger.warning("Ungültiger Wert für STAGED_TTS_INTRO_TIMEOUT: %s", val)
        val = os.getenv("STAGED_TTS_CHUNK_TIMEOUT")
        if val:
            try:
                cfg.chunk_timeout_seconds = int(val)
            except ValueError:
                logger.warning("Ungültiger Wert für STAGED_TTS_CHUNK_TIMEOUT: %s", val)
        return cfg


@dataclass
class StagedPlan:
    intro_engine: str | None = "auto"  # 'auto'|'piper'|'zonos'|None
    main_engine: str | None = "auto"
    fast_start: bool = True


def _env_override(name: str) -> str | None:
    import os
    val = os.getenv(name) or os.getenv(name.lower())
    if not val:
        return None
    v = val.strip().lower()
    return v if v in {"auto", "piper", "zonos", "kokoro", "none", ""} else None


class StagedTTSProcessor:
    """Core class implementing the staged TTS pipeline."""

    def __init__(self, tts_manager, config: StagedTTSConfig | None = None):
        self.plan = StagedPlan()
        self.tts_manager = tts_manager
        self.config = config or StagedTTSConfig.from_env()
        self._cache: "OrderedDict[str, tuple[bytes, int]]" = OrderedDict()

    async def process_staged_tts(self, text: str, canonical_voice: str) -> List[TTSChunk]:
        """Sanitize, chunk and synthesize text in stages."""
        # TODO: unify sanitizer and normalizer steps to avoid duplicate processing
        #       (see TODO-Index.md: WS-Server / Protokolle)
        text = sanitize_for_tts_strict(text)
        text = sanitize_basic(text)

        from .chunking import limit_and_chunk, create_intro_chunk, optimize_for_prosody

        optimized_text = optimize_for_prosody(text)
        chunks = limit_and_chunk(optimized_text, self.config.max_response_length)
        if not chunks:
            logger.warning("Keine Text-Chunks generiert")
            return []

        intro_text, main_chunks = create_intro_chunk(chunks, self.config.max_intro_length)
        sequence_id = uuid.uuid4().hex[:8]
        plan = self._resolve_plan(canonical_voice)
        self.plan = plan

        # Wenn ein Intro-Text vorhanden ist, aber keine Intro-Engine verfügbar,
        # wird der Text als regulärer Haupt-Chunk behandelt.
        if intro_text and not plan.intro_engine and plan.main_engine:
            main_chunks.insert(0, intro_text)
            intro_text = None

        max_main = self.config.max_chunks - (1 if intro_text and plan.intro_engine else 0)
        main_chunks = main_chunks[:max_main]
        total_chunks = (1 if intro_text and plan.intro_engine else 0) + len(main_chunks)

        tasks: list[asyncio.Task] = []
        if intro_text and plan.intro_engine:
            tasks.append(asyncio.create_task(self._synthesize_chunk(
                intro_text, plan.intro_engine, sequence_id, 0, total_chunks, canonical_voice
            )))

        if plan.main_engine:
            offset = 1 if intro_text and plan.intro_engine else 0
            for i, chunk_text in enumerate(main_chunks):
                tasks.append(asyncio.create_task(self._synthesize_chunk(
                    chunk_text, plan.main_engine, sequence_id, i + offset, total_chunks, canonical_voice
                )))
        elif not tasks:
            logger.info("Keine Main-Engine verfügbar – nur Intro wird gespielt.")

        completed = await asyncio.gather(*tasks, return_exceptions=True)
        valid = [c for c in completed if isinstance(c, TTSChunk)]
        valid.sort(key=lambda c: c.index)
        return valid

    async def _synthesize_chunk(
        self,
        text: str,
        engine: str,
        sequence_id: str,
        index: int,
        total: int,
        voice: str,
    ) -> TTSChunk:
        try:
            cache_key = f"{engine}:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"
            if self.config.enable_caching and cache_key in self._cache:
                logger.debug("Cache hit für %s chunk %s", engine, index)
                audio, sr = self._cache.pop(cache_key)
                self._cache[cache_key] = (audio, sr)
                return TTSChunk(sequence_id, index, total, engine, text, audio, True, sr)

            start_time = time.time()
            if engine == "piper":
                text = pre_clean_for_piper(text)
            timeout = (
                self.config.intro_timeout_seconds
                if engine == getattr(self.plan, "intro_engine", None) and index == 0
                else self.config.chunk_timeout_seconds
            )
            try:
                result = await asyncio.wait_for(
                    self.tts_manager.synthesize(text, engine=engine, voice=voice),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                logger.warning("%s TTS Timeout für chunk %s", engine.capitalize(), index)
                collector.tts_sequence_timeout_total.labels(engine=engine).inc()
                return TTSChunk(sequence_id, index, total, engine, text, None, False, 0, "timeout")

            processing_time = time.time() - start_time
            logger.debug("%s TTS chunk %s: %.2fs", engine.capitalize(), index, processing_time)

            if result.success and result.audio_data:
                if self.config.enable_caching:
                    self._cache[cache_key] = (result.audio_data, result.sample_rate)
                    if len(self._cache) > self.config.cache_size:
                        self._cache.popitem(last=False)
                return TTSChunk(sequence_id, index, total, engine, text, result.audio_data, True, result.sample_rate)

            logger.warning("%s TTS fehlgeschlagen für chunk %s: %s", engine.capitalize(), index, result.error_message)
            return TTSChunk(sequence_id, index, total, engine, text, None, False, result.sample_rate, result.error_message)
        except Exception as e:
            logger.error("Fehler bei %s TTS chunk %s: %s", engine, index, e)
            # Engine-Ausfälle für Monitoring mitzählen
            try:
                collector.tts_engine_unavailable_total.labels(engine=engine).inc()
            except Exception:  # pragma: no cover - Metriken optional
                pass
            return TTSChunk(sequence_id, index, total, engine, text, None, False, 0, str(e))

    def create_chunk_message(self, chunk: TTSChunk) -> Dict[str, Any]:
        audio_b64 = ""
        pcm_b64 = ""
        try:
            if chunk.audio_data:
                audio_b64 = base64.b64encode(chunk.audio_data).decode("ascii")
                try:
                    import io
                    import soundfile as sf

                    pcm, _sr = sf.read(io.BytesIO(chunk.audio_data), dtype="float32")
                    if pcm.ndim > 1:
                        pcm = pcm.mean(axis=1)
                    pcm_b64 = base64.b64encode(pcm.tobytes()).decode("ascii")
                except Exception as e:  # pragma: no cover - optional
                    logger.debug(
                        "STAGED_TTS::pcm_encode_failed | seq=%s idx=%s err=%s",
                        chunk.sequence_id,
                        chunk.index,
                        e,
                    )
        except Exception as e:  # pragma: no cover - logging only
            logger.warning(
                "STAGED_TTS::encode_failed | seq=%s idx=%s err=%s",
                chunk.sequence_id,
                chunk.index,
                e,
            )
        if chunk.success and chunk.audio_data:
            try:
                collector.tts_chunk_emitted_total.labels(engine=chunk.engine).inc()
                collector.audio_out_bytes_total.inc(len(chunk.audio_data))
            except Exception:  # pragma: no cover
                pass
        msg = {
            "op": "staged_tts_chunk",
            "type": "tts_chunk",
            "sequence_id": chunk.sequence_id,
            "index": chunk.index,
            "total": chunk.total,
            "engine": chunk.engine,
            "text": chunk.text,
            "pcm": pcm_b64 or None,
            "format": "f32",
            "audio": f"data:audio/wav;base64,{audio_b64}" if audio_b64 else None,
            "sample_rate": chunk.sample_rate,
            "sampleRate": chunk.sample_rate,
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
        msg = {"type": "tts_sequence_end", "sequence_id": sequence_id, "timestamp": time.time()}
        logger.debug("STAGED_TTS::sequence_end | seq=%s", sequence_id)
        return msg

    def get_cache_stats(self) -> Dict[str, Any]:
        total_size = sum(len(data) for data in self._cache.values())
        return {
            "entries": len(self._cache),
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
        }

    def _engine_available_for_voice(self, engine: str, voice: str) -> bool:
        from ws_server.tts.voice_utils import canonicalize_voice

        try:
            engines = getattr(self.tts_manager, "engines", {})
            engine_obj = engines.get(engine)
            if not engine_obj or not getattr(engine_obj, "is_initialized", True):
                return False
            v = canonicalize_voice(voice)
            if hasattr(self.tts_manager, "engine_allowed_for_voice"):
                return bool(self.tts_manager.engine_allowed_for_voice(engine, v))
            return True
        except Exception:
            return False

    def _resolve_plan(self, canonical_voice: str) -> StagedPlan:
        intro = _env_override("STAGED_TTS_INTRO_ENGINE")
        main = _env_override("STAGED_TTS_MAIN_ENGINE")
        try:
            intro = intro or globals().get("INTRO_ENGINE", None)
            main = main or globals().get("MAIN_ENGINE", None)
        except Exception:
            pass
        if intro in ("none", ""): intro = None
        if main in ("none", ""): main = None

        if intro and not self._engine_available_for_voice(intro, canonical_voice):
            logger.info(
                "Intro via %s nicht verfügbar → Intro entfällt, alles %s",
                intro.capitalize(),
                (main or "zonos").capitalize(),
            )
            try:
                collector.tts_intro_engine_unavailable_total.labels(engine=intro).inc()
            except Exception:
                pass
            intro = None
        if main and not self._engine_available_for_voice(main, canonical_voice):
            logger.warning("Main engine '%s' not available for voice '%s'", main, canonical_voice)
            main = None

        plan = StagedPlan(intro_engine=intro or "auto", main_engine=main or "auto", fast_start=True)

        def pick_intro() -> Optional[str]:
            if self._engine_available_for_voice("piper", canonical_voice):
                return "piper"
            return None

        def pick_main() -> Optional[str]:
            if self._engine_available_for_voice("zonos", canonical_voice):
                return "zonos"
            if self._engine_available_for_voice("piper", canonical_voice):
                return "piper"
            return None

        if plan.intro_engine == "auto":
            plan.intro_engine = pick_intro()
        if plan.main_engine == "auto":
            plan.main_engine = pick_main()

        logger.info(
            "STAGED_TTS::plan | intro=%s | main=%s | voice=%s",
            plan.intro_engine,
            plan.main_engine,
            canonical_voice,
        )
        return plan

