#!/usr/bin/env python3
# ruff: noqa: E402
from __future__ import annotations
import os
WS_HOST = os.getenv('WS_HOST','127.0.0.1')
WS_PORT = int(os.getenv('WS_PORT','48231'))
"""Unified WebSocket Audio Streaming Server.

This server consolidates all historic implementations into a single, modern
code base.  It combines low latency audio streaming, real-time STT processing
and runtime switching between Piper and Kokoro TTS engines.  Legacy files
have been moved to ``archive/`` (`ws-server-pre-tts.py`,
`ws-server-old.py`).

Features integrated from previous versions:

* Environment based configuration
* STT audio pre-processing (in-memory ``numpy`` pipeline)
* Intent routing with optional Flowise/n8n calls (``aiohttp``)
* Metrics API und TTS-Engine-Switching

# TODO: clarify whether this legacy compat layer is still needed
#       (see TODO-Index.md: ❓ Offene Fragen)

# Hinweis: Der TTS-Wechsel wird vom ``TTSManager`` verwaltet und
# die Authentifizierung erfolgt über ``auth.token_utils``. Weitere
# Aufteilung in Module ist geplant.

"""

import asyncio
import websockets
# Updated websockets import (v11+ compatibility)
try:
    from websockets.legacy.server import WebSocketServerProtocol
except ImportError:
    from websockets.server import WebSocketServerProtocol
import json
import base64
import time
import uuid
import numpy as np
import os
import logging
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
from collections import deque
import aiohttp
from faster_whisper import WhisperModel
from pathlib import Path
from dotenv import load_dotenv

# --- PYTHONPATH bootstrap (project root) ---
import sys as _sys
from pathlib import Path as _P
_PROJECT_ROOT = _P(__file__).resolve().parents[2]
(_sys.path.insert(0, str(_PROJECT_ROOT))
 if str(_PROJECT_ROOT) not in _sys.path else None)
# ------------------------------------------
from ws_server.tts.manager import TTSManager, TTSEngineType, TTSConfig
from ws_server.tts.voice_validation import validate_voice_assets
from ws_server.tts.staged_tts import StagedTTSProcessor, _limit_and_chunk
from ws_server.tts.staged_tts.staged_processor import StagedTTSConfig
from ws_server.core.prompt import get_system_prompt
from ws_server.audio.vad import VoiceActivityDetector, VADConfig

from ws_server.auth.token import verify_token
from ws_server.metrics.collector import collector
from ws_server.stt import pcm16_bytes_to_float32

# Load environment variables from optional defaults then override with .env
load_dotenv('.env.defaults', override=False)
load_dotenv()

# Set up logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Safe imports with fallbacks removed; modules now live in ws_server.routing
from ws_server.routing.intent_router import IntentClassifier
from ws_server.routing.skills import load_all_skills
from ws_server.metrics.http_api import start_http_server as start_metrics_api
from ws_server.protocol.handshake import parse_client_hello, build_ready

# --- Helpers: Zonos-Language-Normalization & Kokoro-Voice listing ---
def _normalize_zonos_lang():
    import os
    try:
        from zonos.conditioning import supported_language_codes
    except Exception:
        supported_language_codes = set(["de","en-us","fr-fr","es","it","ja","cmn"])
    raw = os.getenv("ZONOS_LANG", "de").strip().lower().replace("_","-")
    m = {
        "de-de": "de", "deu": "de", "ger": "de", "german": "de",
        "en": "en-us", "en_us": "en-us", "en-us": "en-us",
        "en-gb": "en-gb", "uk": "en-gb",
        "fr": "fr-fr", "fra": "fr-fr", "fre": "fr-fr",
        "pt": "pt-br", "pt-br": "pt-br",
        "zh": "cmn", "zh-cn": "cmn",
        "jp": "ja"
    }
    cand = m.get(raw, raw)
    if cand not in supported_language_codes and "-" in cand:
        cand = cand.split("-")[0]
    if cand not in supported_language_codes:
        cand = "en-us" if "en-us" in supported_language_codes else next(iter(sorted(supported_language_codes)))
    os.environ["ZONOS_LANG"] = cand
    return cand

def _kokoro_voice_labels(voices_path: str, model_path: str):
    """Return list of {label, key} from Kokoro voices (safe if Kokoro not installed)."""
    out = []
    try:
        from kokoro_onnx import Kokoro
        tts = Kokoro(model_path, voices_path=voices_path)
        for k in sorted(getattr(tts, "voices", {}).keys()):
            base = k.split("_")
            pretty = base[-1].capitalize() if base else k
            label = f"{pretty} [{k}]"
            out.append({"label": label, "key": k})
    except Exception as exc:
        # TODO-FIXED(2025-08-23): log Kokoro voice detection errors instead of silent pass
        logger.error("Kokoro voice detection failed: %s", exc)
    return out

# --- Minimal LM Studio client -------------------------------------------------
class LMClient:
    def __init__(self, base: str, timeout: int = 20):
        self.base = base.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout)

async def _emit_assistant_text(ws, sequence_id, text):
    """Sende sofort den reinen Assistant-Text an den Client (Text-First UX)."""
    try:
        import time
        import json as _json
        msg = {
            "type": "assistant_text",
            "sequence_id": sequence_id,
            "text": text,
            "timestamp": time.time(),
        }
        await ws.send(_json.dumps(msg))
    except Exception as e:
        logger = globals().get("logger")
        if logger:
            logger.warning("assistant_text emit failed: %s", e)


    async def list_models(self) -> Dict[str, List[str]]:
        """Return available and loaded model identifiers from the LLM service.

        The LM Studio API returns a list of model objects.  Some builds expose a
        ``loaded`` or ``isLoaded`` flag to mark models that are currently
        resident in memory.  This helper normalizes the response to two simple
        lists: ``available`` (all known models) and ``loaded`` (models flagged as
        loaded).  If the service does not expose such a flag the ``loaded`` list
        remains empty.
        """

        url = f"{self.base}/models"
        async with aiohttp.ClientSession(timeout=self.timeout) as s:
            async with s.get(url) as r:
                if r.status != 200:
                    return {"available": [], "loaded": []}
                data = await r.json()
                items = data.get("data", [])
                available = [m.get("id") for m in items if m.get("id")]
                loaded = [
                    m.get("id")
                    for m in items
                    if m.get("id") and (m.get("loaded") or m.get("isLoaded"))
                ]
                return {"available": available, "loaded": loaded}

    async def chat(self, model: str, messages: list, temperature: float = 0.7,
                   max_tokens: int = 256, tools: list | None = None,
                   tool_choice: str | None = None):
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        if tools:
            payload["tools"] = tools
        if tool_choice:
            payload["tool_choice"] = tool_choice
        url = f"{self.base}/chat/completions"
        async with aiohttp.ClientSession(timeout=self.timeout) as s:
            async with s.post(url, json=payload) as r:
                data = await r.json()
                return data

# Normalize ZONOS_LANG after helpers are defined
_normalized_lang = _normalize_zonos_lang()
@dataclass
class StreamingConfig:
    """Configuration read from environment variables."""

    # Audio settings optimized for low latency
    chunk_size: int = int(os.getenv("AUDIO_CHUNK_SIZE", 1024))
    sample_rate: int = int(os.getenv("SAMPLE_RATE", 16000))
    channels: int = int(os.getenv("AUDIO_CHANNELS", 1))
    max_chunk_buffer: int = int(os.getenv("MAX_CHUNK_BUFFER", 50))

    # Processing settings
    stt_workers: int = int(os.getenv("STT_WORKERS", 2))
    max_audio_duration: float = float(os.getenv("MAX_AUDIO_DURATION", 30.0))

    # WebSocket settings
    max_connections: int = int(os.getenv("MAX_CONNECTIONS", 100))
    ping_interval: float = float(os.getenv("PING_INTERVAL", 20.0))
    ping_timeout: float = float(os.getenv("PING_TIMEOUT", 10.0))
    ws_port: int = WS_PORT
    metrics_port: int = int(os.getenv("METRICS_PORT", 48232))

    # Models
    stt_model: str = os.getenv("STT_MODEL", "base")
    stt_model_path: str = os.getenv("STT_MODEL_PATH", "")
    stt_device: str = os.getenv("STT_DEVICE", "cpu")
    stt_precision: str = os.getenv("STT_PRECISION", "int8")

    # TTS Configuration
    # Zonos is the preferred default TTS engine
    default_tts_engine: str = os.getenv("TTS_ENGINE", os.getenv("DEFAULT_TTS_ENGINE", "zonos"))
    default_tts_voice: str = os.getenv("TTS_VOICE", "de-thorsten-low")
    default_tts_speed: float = float(os.getenv("TTS_SPEED", 1.0))
    default_tts_volume: float = float(os.getenv("TTS_VOLUME", 1.0))
    tts_model_dir: str = os.getenv("TTS_MODEL_DIR", "models")
    enable_engine_switching: bool = os.getenv("ENABLE_TTS_SWITCHING", "true").lower() == "true"

    # External services
    flowise_url: str = os.getenv("FLOWISE_URL", "")
    flowise_id: str = os.getenv("FLOWISE_ID", "")
    flowise_token: str = os.getenv("FLOWISE_TOKEN", os.getenv("FLOWISE_API_KEY", ""))
    n8n_url: str = os.getenv("N8N_URL", "")
    n8n_token: str = os.getenv("N8N_TOKEN", "")
    headscale_api: str = os.getenv("HEADSCALE_API", "")
    headscale_token: str = os.getenv("HEADSCALE_TOKEN", "")

    # Local LLM (LM Studio compatible)
    llm_enabled: bool = os.getenv("LLM_ENABLED", "true").lower() == "true"
    llm_api_base: str = os.getenv("LLM_API_BASE", "")
    llm_default_model: str = os.getenv("LLM_DEFAULT_MODEL", "auto")
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", 0.7))
    llm_max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", 256))
    llm_max_turns: int = int(os.getenv("LLM_MAX_TURNS", 5))
    llm_timeout_seconds: int = int(os.getenv("LLM_TIMEOUT_SECONDS", 20))

    # Retry configuration for external services
    retry_limit: int = int(os.getenv("RETRY_LIMIT", 3))
    retry_backoff: float = float(os.getenv("RETRY_BACKOFF", 1.0))

    # Skills and ML
    enabled_skills: List[str] = field(
        default_factory=lambda: [s.strip() for s in os.getenv("ENABLED_SKILLS", "").split(",") if s.strip()]
    )
    intent_model: str = os.getenv("INTENT_MODEL", "models/intent_classifier.bin")

    # Staged TTS Configuration
    staged_tts_enabled: bool = os.getenv("STAGED_TTS_ENABLED", "true").lower() == "true"
    staged_tts_max_response_length: int = int(os.getenv("STAGED_TTS_MAX_RESPONSE_LENGTH", "500"))
    staged_tts_max_intro_length: int = int(os.getenv("STAGED_TTS_MAX_INTRO_LENGTH", "120"))
    staged_tts_chunk_timeout: int = int(os.getenv("STAGED_TTS_CHUNK_TIMEOUT", "10"))
    staged_tts_max_chunks: int = int(os.getenv("STAGED_TTS_MAX_CHUNKS", "3"))
    staged_tts_enable_caching: bool = os.getenv("STAGED_TTS_ENABLE_CACHING", "true").lower() == "true"
    staged_tts_cache_size: int = int(os.getenv("STAGED_TTS_CACHE_SIZE", "256"))
    
    # VAD Configuration
    vad_enabled: bool = os.getenv("VAD_ENABLED", "false").lower() == "true"
    vad_silence_duration_ms: int = int(os.getenv("VAD_SILENCE_DURATION_MS", "1500"))
    vad_energy_threshold: float = float(os.getenv("VAD_ENERGY_THRESHOLD", "0.01"))
    vad_min_speech_duration_ms: int = int(os.getenv("VAD_MIN_SPEECH_DURATION_MS", "500"))
    
    # Binary Audio Support
    enable_binary_audio: bool = os.getenv("ENABLE_BINARY_AUDIO", "false").lower() == "true"

config = StreamingConfig()

ALLOWED_IPS: List[str] = [ip.strip() for ip in os.getenv("ALLOWED_IPS", "").split(",") if ip.strip()]

logger.info(f"Loaded .env profile: {os.getenv('ENV_PROFILE', 'default')}")

class AudioChunk:
    """Audio chunk representation"""
    __slots__ = ['data', 'timestamp', 'sequence', 'client_id']
    
    def __init__(self, data: bytes, timestamp: float, sequence: int, client_id: str):
        self.data = data
        self.timestamp = timestamp
        self.sequence = sequence
        self.client_id = client_id

class AudioBuffer:
    """Memory-efficient circular buffer for audio chunks"""
    
    def __init__(self, max_size: int = 50):
        self.max_size = max_size
        self.buffer: deque = deque(maxlen=max_size)
        self.total_size = 0
        
    def add_chunk(self, chunk: AudioChunk) -> bool:
        """Add chunk, returns False if buffer would overflow"""
        if len(self.buffer) >= self.max_size:
            return False
            
        self.buffer.append(chunk)
        self.total_size += len(chunk.data)
        return True
        
    def get_all_audio(self) -> bytes:
        """Combine all chunks into single audio stream"""
        if not self.buffer:
            return b''
            
        # Sort by sequence number to handle out-of-order chunks
        sorted_chunks = sorted(self.buffer, key=lambda x: x.sequence)
        return b''.join(chunk.data for chunk in sorted_chunks)
        
    def clear(self):
        """Clear buffer and reset counters"""
        self.buffer.clear()
        self.total_size = 0
        
    def __len__(self):
        return len(self.buffer)

class AsyncSTTEngine:
    """Non-blocking STT engine with worker pool and preprocessing."""

    def __init__(self, model_size: str = "base", model_path: str = "", device: str = "cpu", workers: int = 2):
        self.model_size = model_size
        self.model_path = model_path
        self.device = device
        self.executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="STT")
        self.model = None
        self._model_lock = asyncio.Lock()
        
    async def initialize(self):
        """Initialize model in thread pool to avoid blocking"""
        loop = asyncio.get_event_loop()
        self.model = await loop.run_in_executor(
            self.executor,
            self._load_model
        )
        logger.info(f"STT model '{self.model_size}' loaded on {self.device}")
        
    def _load_model(self) -> WhisperModel:
        """Load model synchronously in worker thread"""
        target = self.model_path if self.model_path else self.model_size

        # Some Hugging Face repositories such as "openai/whisper-base" only ship
        # the original PyTorch weights.  Those do not contain the required
        # CTranslate2 files used by faster-whisper.  Detect such names early and
        # redirect to the official faster-whisper repositories to avoid startup
        # warnings and failed first attempts.
        if not self.model_path and target.startswith("openai/whisper-"):
            base_name = target.split("/")[-1].replace("whisper-", "")
            alt = f"Systran/faster-whisper-{base_name}"
            logger.info(
                f"Using faster-whisper model '{alt}' instead of '{target}'"
            )
            target = alt

        try:
            return WhisperModel(
                target,
                device=self.device,
                compute_type=config.stt_precision
            )
        except RuntimeError as exc:
            # If the downloaded model is missing the CTranslate2 files (model.bin),
            # fall back to the official faster-whisper repository which provides
            # ready-to-use converted models. This prevents startup failures when
            # a PyTorch model repository is mistakenly used.
            if "model.bin" in str(exc) and not self.model_path:
                base_name = target.split("/")[-1].replace("whisper-", "")
                alt = f"Systran/faster-whisper-{base_name}"
                if target != alt:
                    logger.warning(
                        f"CT2 model not found for '{target}', trying fallback '{alt}'"
                    )
                    return WhisperModel(
                        alt,
                        device=self.device,
                        compute_type=config.stt_precision
                    )
            raise
        
    async def transcribe_audio(self, audio_data: bytes) -> str:
        """Transcribe audio without blocking event loop."""
        if not self.model:
            raise RuntimeError("STT model not initialized")

        loop = asyncio.get_event_loop()

        try:
            # Preprocess audio before sending to the worker thread
            processed = self._preprocess_audio(audio_data)

            start_time = time.time()
            result = await loop.run_in_executor(
                self.executor,
                self._transcribe_sync,
                processed
            )

            processing_time = time.time() - start_time
            logger.debug(f"STT processing took {processing_time:.2f}s")

            return result

        except Exception as e:
            logger.error(f"STT transcription failed: {e}")
            return f"[STT Error: {str(e)}]"

    def _preprocess_audio(self, audio_bytes: bytes) -> np.ndarray:
        """Convert raw PCM16 bytes to normalized float32 array."""
        return pcm16_bytes_to_float32(audio_bytes)

    async def process_binary_audio(
        self, audio_data: bytes, *, stream_id: str = "", sequence: int = 0, **_kwargs
    ) -> dict | None:
        """Transcribe a PCM16 audio chunk without buffering the whole stream."""
        # TODO-FIXED(2025-08-23): stream chunk-wise without buffering entire audio
        text = await self.transcribe_audio(audio_data)
        return {"text": text} if text else None

    def _transcribe_sync(self, audio_array: np.ndarray) -> str:
        """Synchronous transcription in worker thread."""
        try:
            segments, info = self.model.transcribe(
                audio_array,
                language="de",
                beam_size=5,
                sample_rate=config.sample_rate
            )
            text = "".join(segment.text for segment in segments).strip()
            return text or "(no speech detected)"
        except Exception as e:
            logger.error(f"Sync transcription error: {e}")
            return f"[Transcription failed: {str(e)}]"

class AudioStreamManager:
    """Manages real-time audio streams with minimal latency"""
    
    def __init__(self, stt_engine: AsyncSTTEngine, tts_manager: "TTSManager"):
        self.stt_engine = stt_engine
        self.tts_manager = tts_manager
        self.active_streams: Dict[str, Dict] = {}
        self.processing_queue = asyncio.Queue(maxsize=1000)
        self.response_callbacks: Dict[str, callable] = {}
        
        # VAD support
        self.vad_processors: Dict[str, VoiceActivityDetector] = {}
        self.vad_enabled = config.vad_enabled

        # Skills und Intent-Klassifizierer laden
        skills_path = Path(__file__).parent / "skills"
        self.skills = load_all_skills(skills_path, config.enabled_skills)
        if config.enabled_skills:
            logger.info("Aktive Skills: %s", ", ".join(type(s).__name__ for s in self.skills))
        self.intent_classifier = IntentClassifier(config.intent_model)

        # Start background processor (nur wenn bereits ein Loop läuft)
        self._queue_task = None
        try:
            loop = asyncio.get_running_loop()
            self._queue_task = loop.create_task(self._process_audio_queue())
        except RuntimeError:
            # wird in VoiceServer.initialize() gestartet
            pass

    async def start_stream(self, client_id: str, response_callback) -> str:
        """Start new audio stream for client"""
        stream_id = f"{client_id}_{uuid.uuid4().hex[:8]}"
        
        self.active_streams[stream_id] = {
            'client_id': client_id,
            'buffer': AudioBuffer(max_size=config.max_chunk_buffer),
            'start_time': time.time(),
            'last_activity': time.time(),
            'is_active': True,
            'chunk_count': 0,
            'tts_engine': None,  # Client-spezifische TTS-Engine
            'tts_voice': None,   # Client-spezifische Stimme
            'tts_speed': None,
            'tts_volume': None,
            'vad_enabled': False,  # Per-stream VAD setting
            'vad_auto_stop_triggered': False
        }
        
        # Initialize VAD processor if enabled
        if self.vad_enabled:
            vad_config = VADConfig(
                sample_rate=config.sample_rate,
                silence_duration_ms=config.vad_silence_duration_ms,
                energy_threshold=config.vad_energy_threshold,
                min_speech_duration_ms=config.vad_min_speech_duration_ms
            )
            self.vad_processors[stream_id] = VoiceActivityDetector(vad_config)
            self.active_streams[stream_id]['vad_enabled'] = True
            logger.debug(f"VAD processor initialized for stream {stream_id}")
        
        self.response_callbacks[stream_id] = response_callback
        logger.debug(f"Started audio stream {stream_id} for client {client_id}")
        
        return stream_id
        
    async def add_audio_chunk(self, stream_id: str, chunk_data: bytes, sequence: int, 
                            is_binary: bool = False) -> bool:
        """Add audio chunk to stream buffer with VAD processing"""
        if stream_id not in self.active_streams:
            return False
            
        stream = self.active_streams[stream_id]
        
        # Check if stream is still valid
        if not stream['is_active']:
            return False
            
        # Check if VAD auto-stop was already triggered
        if stream.get('vad_auto_stop_triggered', False):
            logger.debug(f"Stream {stream_id} auto-stopped by VAD")
            return False
            
        # Check duration limit
        if time.time() - stream['start_time'] > config.max_audio_duration:
            logger.warning(f"Stream {stream_id} exceeded max duration")
            return False
        
        # VAD processing if enabled for this stream
        if stream.get('vad_enabled', False) and stream_id in self.vad_processors:
            try:
                # Convert audio data to numpy array for VAD processing
                if is_binary:
                    # Binary PCM16 data
                    audio_np = np.frombuffer(chunk_data, dtype=np.int16).astype(np.float32) / 32768.0
                else:
                    # JSON base64 data (already converted to bytes)
                    audio_np = np.frombuffer(chunk_data, dtype=np.int16).astype(np.float32) / 32768.0
                
                # Process through VAD
                vad_processor = self.vad_processors[stream_id]
                should_continue = vad_processor.process_frame(audio_np)
                
                if not should_continue:
                    logger.info(f"VAD triggered auto-stop for stream {stream_id}")
                    stream['vad_auto_stop_triggered'] = True
                    # Trigger finalization
                    asyncio.create_task(self.finalize_stream(stream_id))
                    return False
                    
            except Exception as e:
                logger.error(f"VAD processing error for stream {stream_id}: {e}")
                # Continue without VAD on error
            
        # Create optimized chunk
        chunk = AudioChunk(
            data=chunk_data,
            timestamp=time.time(),
            sequence=sequence,
            client_id=stream['client_id']
        )
        
        # Add to buffer
        if stream['buffer'].add_chunk(chunk):
            stream['last_activity'] = time.time()
            stream['chunk_count'] += 1
            return True
        else:
            logger.warning(f"Buffer full for stream {stream_id}")
            return False
            
    async def finalize_stream(self, stream_id: str) -> bool:
        """Finalize stream and queue for processing"""
        if stream_id not in self.active_streams:
            return False
            
        stream = self.active_streams[stream_id]
        stream['is_active'] = False
        
        # Get combined audio data
        audio_data = stream['buffer'].get_all_audio()
        
        if audio_data:
            # Queue for processing
            try:
                await self.processing_queue.put({
                    'stream_id': stream_id,
                    'audio_data': audio_data,
                    'client_id': stream['client_id'],
                    'chunk_count': stream['chunk_count'],
                    'tts_engine': stream.get('tts_engine'),
                    'tts_voice': stream.get('tts_voice'),
                    'tts_speed': stream.get('tts_speed'),
                    'tts_volume': stream.get('tts_volume')
                })
                logger.debug(f"Queued stream {stream_id} for processing ({len(audio_data)} bytes)")
                return True
            except asyncio.QueueFull:
                logger.error(f"Processing queue full, dropping stream {stream_id}")
                return False
        else:
            logger.warning(f"No audio data in finalized stream {stream_id}")
            return False
            
    async def set_stream_tts_config(self, stream_id: str, engine: Optional[str] = None,
                                    voice: Optional[str] = None, speed: Optional[float] = None,
                                    volume: Optional[float] = None):
        """Setze TTS-Konfiguration für Stream"""
        if stream_id in self.active_streams:
            if engine:
                self.active_streams[stream_id]['tts_engine'] = engine
            if voice:
                self.active_streams[stream_id]['tts_voice'] = voice
            if speed is not None:
                self.active_streams[stream_id]['tts_speed'] = speed
            if volume is not None:
                self.active_streams[stream_id]['tts_volume'] = volume
                
    async def _process_audio_queue(self):
        """Background processor for audio streams"""
        while True:
            try:
                # Get next item from queue
                item = await self.processing_queue.get()
                
                # Process in background without blocking
                asyncio.create_task(self._process_audio_item(item))
                
            except Exception as e:
                logger.error(f"Audio queue processor error: {e}")
                await asyncio.sleep(1)
                
    async def _process_audio_item(self, item: Dict):
        """Process individual audio item"""
        stream_id = item['stream_id']
        audio_data = item['audio_data']
        client_id = item['client_id']
        tts_engine = item.get('tts_engine')
        tts_voice = item.get('tts_voice')
        tts_speed = item.get('tts_speed')
        tts_volume = item.get('tts_volume')
        
        try:
            start_time = time.time()

            stt_start = time.time()
            transcription = await self.stt_engine.transcribe_audio(audio_data)
            stt_latency = (time.time() - stt_start) * 1000
            self.stats['stt_latency_ms'].append(stt_latency)
            if len(self.stats['stt_latency_ms']) > 100:
                self.stats['stt_latency_ms'].pop(0)

            response_text = await server._ask_llm(client_id, transcription)
            if not response_text:
                response_text = await self._generate_response(transcription, client_id)

            target_engine = None
            if tts_engine:
                t = tts_engine.lower()
                if t == 'piper':
                    target_engine = TTSEngineType.PIPER
                elif t == 'kokoro':
                    target_engine = TTSEngineType.KOKORO
                elif t == 'zonos':
                    target_engine = TTSEngineType.ZONOS

            tts_kwargs = {}
            if tts_speed is not None:
                tts_kwargs['speed'] = tts_speed
            if tts_volume is not None:
                tts_kwargs['volume'] = tts_volume
            tts_start = time.time()
            tts_result = await self.tts_manager.synthesize(
                response_text,
                engine=target_engine,
                voice=tts_voice,
                **tts_kwargs
            )
            tts_latency = (time.time() - tts_start) * 1000
            self.stats['tts_latency_ms'].append(tts_latency)
            if len(self.stats['tts_latency_ms']) > 100:
                self.stats['tts_latency_ms'].pop(0)

            processing_time = time.time() - start_time
            logger.info(f"Processed stream {stream_id} in {processing_time:.2f}s: '{transcription[:50]}...'")
            
            # Send response via callback
            callback = self.response_callbacks.get(stream_id)
            if callback:
                await callback({
                    'type': 'audio_response',
                    'transcription': transcription,
                    'response_text': response_text,
                    'audio_data': tts_result.audio_data if tts_result.success else None,
                    'processing_time_ms': round(processing_time * 1000),
                    'tts_engine_used': tts_result.engine_used,
                    'tts_voice_used': tts_result.voice_used,
                    'tts_success': tts_result.success,
                    'tts_error': tts_result.error_message if not tts_result.success else None,
                    'stream_id': stream_id
                })
                
        except Exception as e:
            logger.error(f"Error processing audio item {stream_id}: {e}")
            
        finally:
            # Cleanup
            if stream_id in self.active_streams:
                del self.active_streams[stream_id]
            if stream_id in self.response_callbacks:
                del self.response_callbacks[stream_id]
            if stream_id in self.vad_processors:
                del self.vad_processors[stream_id]
                
    async def _generate_response(self, transcription: str, client_id: str) -> str:
        """Generate response using Skills, ML classification and external routing."""
        if not transcription or transcription.startswith('['):
            return "Entschuldigung, ich konnte Sie nicht verstehen."

        text = transcription.lower().strip()

        intent_result = self.intent_classifier.classify(text)
        intent = intent_result.intent if intent_result.confidence >= 0.5 else "unknown"
        logger.info(
            "Intent erkannt: %s (%.2f)", intent, intent_result.confidence
        )

        if intent == "external_request":
            logger.info("Routing decision: external")
            external = await self._route_external(text, client_id)
            if external:
                return external

        for skill in self.skills:
            if getattr(skill, "intent_name", None) == intent:
                logger.info("Routing decision: skill %s", skill.__class__.__name__)
                return skill.handle(text)

        for skill in self.skills:
            if skill.can_handle(text):
                logger.info("Routing decision: skill %s", skill.__class__.__name__)
                return skill.handle(text)

        logger.info("Routing decision: fallback response")
        return "Entschuldigung, dafür habe ich keine Antwort."

    async def _route_external(self, text: str, client_id: str) -> Optional[str]:
        if config.flowise_url and config.flowise_id:
            logger.info("Routing external via Flowise")
            return await self._ask_flowise(text, client_id)
        if config.n8n_url:
            logger.info("Routing external via n8n")
            return await self._trigger_n8n(text, client_id)
        logger.info("No external routing configured")
        return None

    async def _ask_flowise(self, query: str, client_id: str) -> str:
        """Send query to Flowise REST API."""
        url = f"{config.flowise_url}/api/v1/prediction/{config.flowise_id}"
        headers = {"Content-Type": "application/json"}
        if config.flowise_token:
            headers["Authorization"] = f"Bearer {config.flowise_token}"
        payload = {"question": query, "sessionId": client_id}
        for attempt in range(1, config.retry_limit + 1):
            try:
                timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(url, headers=headers, json=payload) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            return data.get("text") or data.get("answer") or "(keine Antwort von Flowise)"
                        return f"[Flowise Fehler {resp.status}]"
            except asyncio.TimeoutError:
                logger.error("Flowise request timed out")
            except Exception:
                logging.exception("Flowise request failed")
            if attempt < config.retry_limit:
                await asyncio.sleep(config.retry_backoff * (2 ** (attempt - 1)))
        logger.error("Flowise not reachable after retries")
        return "Fehler: Flowise nicht erreichbar"

    async def _trigger_n8n(self, query: str, client_id: str) -> str:
        """Trigger n8n webhook with the given query."""
        payload = {"query": query, "sessionId": client_id}
        headers = {"Content-Type": "application/json"}
        if config.n8n_token:
            headers["Authorization"] = f"Bearer {config.n8n_token}"
        for attempt in range(1, config.retry_limit + 1):
            try:
                timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(config.n8n_url, headers=headers, json=payload) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            return data.get("reply", "OK, erledigt")
                        return f"[n8n Fehler {resp.status}]"
            except asyncio.TimeoutError:
                logger.error("n8n request timed out")
            except Exception:
                logging.exception("n8n request failed")
            if attempt < config.retry_limit:
                await asyncio.sleep(config.retry_backoff * (2 ** (attempt - 1)))
        return "(n8n nicht erreichbar)"

class ConnectionManager:
    """Manages WebSocket connections with optimized handling"""
    
    def __init__(self, stream_manager: AudioStreamManager, tts_manager: "TTSManager"):
        self.active_connections: Dict[str, WebSocketServerProtocol] = {}
        self.connection_info: Dict[str, Dict] = {}
        self.stream_manager = stream_manager
        self.tts_manager = tts_manager
        
    async def register(self, websocket: WebSocketServerProtocol) -> str:
        """Register new WebSocket connection"""
        client_id = uuid.uuid4().hex
        
        self.active_connections[client_id] = websocket
        self.connection_info[client_id] = {
            'connected_at': time.time(),
            'last_activity': time.time(),
            'remote_addr': websocket.remote_address[0] if websocket.remote_address else 'unknown',
            'messages_sent': 0,
            'messages_received': 0,
            'preferred_tts_engine': config.default_tts_engine,
            'preferred_tts_voice': config.default_tts_voice,
            'preferred_tts_speed': config.default_tts_speed,
            'preferred_tts_volume': config.default_tts_volume
        }
        
        logger.info(f"Client {client_id} connected from {websocket.remote_address}")
        return client_id
        
    async def unregister(self, client_id: str):
        """Unregister WebSocket connection"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            
        if client_id in self.connection_info:
            del self.connection_info[client_id]
            
        logger.info(f"Client {client_id} disconnected")
        
    async def send_to_client(self, client_id: str, message: Dict) -> bool:
        """Send message to specific client"""
        if client_id not in self.active_connections:
            return False
            
        try:
            websocket = self.active_connections[client_id]
            await websocket.send(json.dumps(message))

            # Update stats
            self.connection_info[client_id]['messages_sent'] += 1
            self.connection_info[client_id]['last_activity'] = time.time()

            return True

        except websockets.exceptions.ConnectionClosed:
            await self.unregister(client_id)
            return False
        except Exception as e:
            logger.error(f"Error sending to client {client_id}: {e}")
            for attempt in range(1, 4):
                try:
                    await asyncio.sleep(0.5 * attempt)
                    await websocket.send(json.dumps(message))
                    logger.info("Retry to client %s succeeded on attempt %s", client_id, attempt)
                    return True
                except Exception:
                    continue
            logger.warning("Failed to deliver message to %s, closing connection", client_id)
            await self.unregister(client_id)
            return False

class VoiceServer:
    """Main server with audio streaming and TTS switching"""
    
    def __init__(self):
        self.stt_engine = AsyncSTTEngine(
            model_size=config.stt_model,
            model_path=config.stt_model_path,
            device=config.stt_device,
            workers=config.stt_workers
        )
        
        # Initialisiere TTS-Manager mit Fallback
        try:
            self.tts_manager = TTSManager()
            logger.info("✅ TTSManager created successfully")
            canonical_voice = os.getenv("TTS_VOICE", "de-thorsten-low")
            for msg in validate_voice_assets(canonical_voice):
                logger.info(msg)
        except Exception as e:
            logger.error(f"❌ TTSManager creation failed: {e}")
            # Create dummy TTS manager for testing
            class DummyTTSManager:
                async def initialize(self, *args, **kwargs):
                    return True
                async def synthesize(self, *args, **kwargs):
                    from backend.tts.base_tts_engine import TTSResult
                    return TTSResult(success=False, error_message="TTS not available")
                async def cleanup(self):
                    pass
                def get_available_engines(self):
                    return []
                def get_current_engine(self):
                    return None
                def get_engine_stats(self):
                    return {}
                async def switch_engine(self, *args):
                    return False
                async def set_voice(self, *args):
                    return False
                async def test_all_engines(self, *args):
                    return {}
            self.tts_manager = DummyTTSManager()
            logger.warning("⚠️  Using dummy TTS manager - TTS features disabled")
        
        # Initialize Staged TTS Processor
        staged_tts_config = StagedTTSConfig(
            enabled=config.staged_tts_enabled,
            max_response_length=config.staged_tts_max_response_length,
            max_intro_length=config.staged_tts_max_intro_length,
            chunk_timeout_seconds=config.staged_tts_chunk_timeout,
            max_chunks=config.staged_tts_max_chunks,
            enable_caching=config.staged_tts_enable_caching,
            cache_size=config.staged_tts_cache_size
        )
        self.staged_tts = StagedTTSProcessor(self.tts_manager, staged_tts_config)
        logger.info(f"🎭 Staged TTS: {'enabled' if config.staged_tts_enabled else 'disabled'}")
        
        self.stream_manager = AudioStreamManager(self.stt_engine, self.tts_manager)
        # self.stream_manager.stats wird weiter unten gesetzt, nachdem self.stats existiert
        self.connection_manager = ConnectionManager(self.stream_manager, self.tts_manager)

        # LLM configuration
        self.llm_enabled = config.llm_enabled
        self.llm = LMClient(config.llm_api_base, timeout=config.llm_timeout_seconds)
        self.llm_model: Optional[str] = None
        self.llm_models: List[str] = []
        self.chat_histories: Dict[str, List[Dict[str, str]]] = {}
        self.llm_temperature = config.llm_temperature
        self.llm_max_tokens = config.llm_max_tokens
        self.llm_max_turns = config.llm_max_turns

        # Performance metrics
        self.stats = {
            'connections': 0,
            'messages_processed': 0,
            'audio_streams': 0,
            'tts_switches': 0,
            'stt_latency_ms': [],
            'tts_latency_ms': [],
            'start_time': time.time()
        }
        # jetzt dem Stream-Manager zuweisen
        self.stream_manager.stats = self.stats
        
    async def initialize(self):
        """Initialize all components"""
        logger.info("Initializing voice server with TTS switching...")
        
        # Initialize STT engine
        logger.info("🎤 Initialisiere STT Engine...")
        await self.stt_engine.initialize()
        logger.info("✅ STT Engine initialisiert")
        
        # Initialize TTS Manager
        # Standard-Konfigurationen für beide Engines
        piper_config = TTSConfig(
            engine_type="piper",
            model_path="",  # Wird automatisch ermittelt
            voice=config.default_tts_voice,
            speed=config.default_tts_speed,
            volume=config.default_tts_volume,
            language="de",
            sample_rate=22050,
            model_dir=config.tts_model_dir
        )

        kokoro_config = TTSConfig(
            engine_type="kokoro",
            model_path="",  # Wird automatisch ermittelt
            voice="af_sarah",
            speed=config.default_tts_speed,
            volume=config.default_tts_volume,
            language="en",
            sample_rate=24000,
            model_dir=config.tts_model_dir
        )

        zonos_config = TTSConfig(
            engine_type="zonos",
            model_path=os.getenv("ZONOS_MODEL", "Zyphra/Zonos-v0.1-transformer"),
            voice=os.getenv("ZONOS_VOICE", "thorsten"),
            speed=config.default_tts_speed,
            volume=config.default_tts_volume,
            language=os.getenv("ZONOS_LANG", "de"),
            sample_rate=int(os.getenv("TTS_OUTPUT_SR", 48000)),
            model_dir=config.tts_model_dir,
            engine_params={"speaker_dir": os.getenv("ZONOS_SPEAKER_DIR", "spk_cache")}
        )
        
        # Bestimme Standard-Engine
        _de=(config.default_tts_engine or 'piper').lower()
        if _de=='piper':
            default_engine=TTSEngineType.PIPER
        elif _de=='kokoro':
            default_engine=TTSEngineType.KOKORO
        elif _de=='zonos':
            default_engine=TTSEngineType.ZONOS
        else:
            default_engine=TTSEngineType.PIPER
        
        logger.info("🎧 Starte TTS-Manager Initialisierung...")
        success = await self.tts_manager.initialize(piper_config, kokoro_config, zonos_config, default_engine=default_engine)
        if success:
            logger.info("✅ TTS-Manager erfolgreich initialisiert")
        else:
            logger.error("❌ TTS-Manager Initialisierung fehlgeschlagen!")

        # Sicherstellen, dass der Audio-Queue-Prozessor läuft
        if getattr(self.stream_manager, "_queue_task", None) is None:
            self.stream_manager._queue_task = asyncio.create_task(self.stream_manager._process_audio_queue())

        # Optional Headscale connection check
        if config.headscale_api:
            headers = {}
            if config.headscale_token:
                headers["Authorization"] = f"Bearer {config.headscale_token}"
            try:
                timeout = aiohttp.ClientTimeout(total=5)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(f"{config.headscale_api}/machines", headers=headers) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            nodes = [m.get("id") for m in data.get("machines", [])]
                            logger.info(f"Headscale nodes available: {nodes}")
                        else:
                            logger.warning(f"Headscale check failed: {resp.status}")
            except Exception as e:
                logger.warning(f"Headscale connection failed: {e}")

        logger.info("🎆 Audio Queue Processor gestartet")

        if self.llm_enabled:
            import logging
            try:
                # Discovery optional; LMClient hat self.llm.base bereits gesetzt.
                info = await self.llm.list_models()
            except Exception as e:
                logging.getLogger(__name__).warning(
                    "LLM discovery failed: %s — continuing without LLM list. Set LLM_BASE_URL or config.llm_api_base.", e
                )
                info = {"available": [], "data": [], "loaded": []}

            # Normalisieren: unterstütze sowohl {"available": [...]} als auch {"data": [...]}
            self.llm_models = info.get('available', []) or info.get('data', [])
            chosen = None
            pref = config.llm_default_model
            if pref != "auto" and pref in self.llm_models:
                chosen = pref
            elif self.llm_models:
                chosen = self.llm_models[0]
            self.llm_model = chosen
            if chosen:
                logger.info(f"LLM enabled. Using model: {chosen}")
            else:
                logger.warning("LLM enabled but no loaded models found; will fallback to skills/legacy responses.")


        # Abschließende Initialisierung
        logger.info("✨ Voice server initialized successfully")

    def _hist(self, client_id: str):
        return self.chat_histories.setdefault(client_id, [])

    def _hist_trim(self, client_id: str):
        hist = self._hist(client_id)
        if len(hist) > 2 * self.llm_max_turns + 1:
            sys = hist[0] if hist and hist[0].get("role") == "system" else None
            tail = hist[-(2 * self.llm_max_turns):]
            self.chat_histories[client_id] = ([sys] + tail) if sys else tail

    async def _ask_llm(self, client_id: str, user_text: str) -> Optional[str]:
        if not (self.llm_enabled and self.llm_model):
            return None

        msgs = self._hist(client_id)
        if not msgs or msgs[0].get("role") != "system":
            msgs.insert(0, {"role": "system", "content": get_system_prompt()})
        msgs.append({"role": "user", "content": user_text})
        self._hist_trim(client_id)

        try:
            resp = await self.llm.chat(
                model=self.llm_model,
                messages=msgs,
                temperature=self.llm_temperature,
                max_tokens=self.llm_max_tokens
            )
            choice = (resp.get("choices") or [{}])[0]
            msg = choice.get("message") or {}
            content = msg.get("content") or ""
            if content.strip():
                capped = " ".join(_limit_and_chunk(content))
                msgs.append({"role": "assistant", "content": capped})
                self._hist_trim(client_id)
                return capped
        except Exception:
            logging.exception("LLM chat failed")
        return None
        
    async def handle_websocket(self, websocket, path=None):
        # --- websockets v11+ compat: 'path' wird nicht mehr übergeben ---
        if path is None:
            try:
                path = getattr(websocket, 'path', '/')
            except Exception:
                path = '/'
        """Handle WebSocket connection with optimized message processing"""
        from urllib.parse import urlparse, parse_qs

        client_ip = websocket.remote_address[0] if websocket.remote_address else ""
        if ALLOWED_IPS and client_ip not in ALLOWED_IPS:
            logger.warning("Unauthorized IP %s", client_ip)
            await websocket.close(code=4401, reason="unauthorized")
            return

        # --- Token extraction -------------------------------------------------
        # websockets>=15 no longer passes the request path (including the query
        # string) as the ``path`` argument.  Instead the information is exposed
        # via ``websocket.request.path``.  To remain compatible with older
        # versions we try a number of attributes in order of preference.
        raw_path = path or '/'
        try:
            request = getattr(websocket, 'request', None)
            if request and getattr(request, 'path', None):
                raw_path = request.path
            else:
                raw_path = getattr(websocket, 'path', raw_path)
        except Exception:
            raw_path = getattr(websocket, 'path', raw_path)

        query = parse_qs(urlparse(raw_path).query)
        token = query.get('token', [None])[0]
        if not token:
            auth = websocket.request_headers.get('Authorization') if hasattr(websocket, 'request_headers') else None
            if auth and auth.lower().startswith('bearer '):
                token = auth[7:].strip()
        if not token and getattr(websocket, 'subprotocol', None):
            token = websocket.subprotocol

        logger.info("WS connect path=%s token=%s", raw_path, token)

        if not verify_token(token):
            await websocket.close(code=4401, reason="unauthorized")
            return

        client_id = await self.connection_manager.register(websocket)
        collector.active_connections.inc()

        try:
            # ---- Handshake ---------------------------------------------------
            # Erwartet erste Nachricht: {op:"hello", version, stream_id, device}
            raw = await asyncio.wait_for(websocket.recv(), timeout=10)
            try:
                hello = json.loads(raw)
                parse_client_hello(hello)
            except Exception:
                logger.warning("Invalid handshake JSON from %s: %s", client_ip, raw)
                await websocket.close(code=4400, reason="bad handshake")
                return

            await self.connection_manager.send_to_client(
                client_id,
                build_ready({"binary_audio": True}),
            )

            # Optional: zusätzliche Verbindungsinformationen
            available_engines = await self.tts_manager.get_available_engines()
            current_engine = self.tts_manager.get_current_engine()
            current_engine_str = current_engine.value if current_engine else None
            await self.connection_manager.send_to_client(client_id, {
                'type': 'connected',
                'client_id': client_id,
                'server_time': time.time(),
                'config': {
                    'chunk_size': config.chunk_size,
                    'sample_rate': config.sample_rate,
                    'max_duration': config.max_audio_duration,
                    'tts_switching_enabled': config.enable_engine_switching
                },
                'tts_info': {
                    'available_engines': available_engines,
                    'current_engine': current_engine_str,
                    'switching_enabled': config.enable_engine_switching
                }
            })

            # Message handling loop
            async for message in websocket:
                try:
                    data = json.loads(message)
                    collector.messages_total.labels(protocol="json").inc()
                    await self._handle_message(client_id, data)

                    # Update stats
                    info = self.connection_manager.connection_info[client_id]
                    info['messages_received'] += 1
                    info['last_activity'] = time.time()
                    self.stats['messages_processed'] += 1

                except json.JSONDecodeError:
                    await self.connection_manager.send_to_client(client_id, {
                        'type': 'error',
                        'message': 'Invalid JSON format'
                    })
                except Exception:
                    logging.exception("Unhandled error during message processing")
                    await self.connection_manager.send_to_client(client_id, {
                        'type': 'error',
                        'message': 'internal server error'
                    })
                    break

        except asyncio.TimeoutError:
            logger.warning("Handshake timeout for %s", client_id)
            try:
                await websocket.close(code=4408, reason="handshake timeout")
            except Exception:
                pass
        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"Client {client_id} connection closed: {e.code} {e.reason}")
        except Exception:
            logger.exception("WS session error")
            try:
                await websocket.close(code=1011, reason="server error")
            except Exception:
                pass
        finally:
            await self.connection_manager.unregister(client_id)
            collector.active_connections.dec()
            
    async def _handle_message(self, client_id: str, data: Dict):
        """Handle individual WebSocket message"""
        message_type = data.get('type')
        
        if message_type == 'start_audio_stream':
            await self._handle_start_audio_stream(client_id, data)
        elif message_type == 'audio_chunk':
            await self._handle_audio_chunk(client_id, data)
        elif message_type == 'end_audio_stream':
            await self._handle_end_audio_stream(client_id, data)
        elif message_type == 'text':
            await self._handle_text_message(client_id, data)
        elif message_type == 'switch_tts_engine':
            await self._handle_switch_tts_engine(client_id, data)
        elif message_type == 'get_tts_info':
            await self._handle_get_tts_info(client_id, data)
        elif message_type == 'set_tts_voice':
            await self._handle_set_tts_voice(client_id, data)
        elif message_type == 'test_tts_engines':
            await self._handle_test_tts_engines(client_id, data)
        elif message_type == 'get_llm_models':
            await self._handle_get_llm_models(client_id, data)
        elif message_type == 'switch_llm_model':
            await self._handle_switch_llm_model(client_id, data)
        elif message_type == 'staged_tts_control':
            await self._handle_staged_tts_control(client_id, data)
        elif message_type == 'get_stt_models':
            await self._handle_get_stt_models(client_id, data)
        elif message_type == 'switch_stt_model':
            await self._handle_switch_stt_model(client_id, data)
        elif message_type == 'set_audio_opts':
            await self._handle_set_audio_opts(client_id, data)
        elif message_type == 'set_llm_opts':
            await self._handle_set_llm_opts(client_id, data)
        elif message_type == 'ping':
            await self._handle_ping(client_id, data)
        else:
            await self.connection_manager.send_to_client(client_id, {
                'type': 'error',
                'message': f'Unknown message type: {message_type}'
            })
            
    async def _handle_start_audio_stream(self, client_id: str, data: Dict):
        """Start new audio stream"""
        # TTS-Konfiguration aus Client-Einstellungen
        tts_engine = data.get('tts_engine')
        tts_voice = data.get('tts_voice')
        tts_speed = data.get('tts_speed')
        tts_volume = data.get('tts_volume')
        if any(v is not None for v in [tts_engine, tts_voice, tts_speed, tts_volume]):
            logger.info(
                f"Using dynamic TTS params: engine={tts_engine}, voice={tts_voice}, "
                f"speed={tts_speed}, volume={tts_volume}"
            )
        
        # Create response callback
        async def response_callback(response_data):
            await self._send_audio_response(client_id, response_data)
            
        stream_id = await self.stream_manager.start_stream(client_id, response_callback)
        
        # TTS-Konfiguration für Stream setzen
        await self.stream_manager.set_stream_tts_config(
            stream_id,
            tts_engine,
            tts_voice,
            tts_speed,
            tts_volume
        )
        
        await self.connection_manager.send_to_client(client_id, {
            'type': 'audio_stream_started',
            'stream_id': stream_id,
            'tts_engine': tts_engine,
            'tts_voice': tts_voice,
            'tts_speed': tts_speed,
            'tts_volume': tts_volume,
            'timestamp': time.time()
        })
        
        self.stats['audio_streams'] += 1
        
    async def _handle_audio_chunk(self, client_id: str, data: Dict):
        """Handle incoming audio chunk (JSON base64 or binary)"""
        stream_id = data.get('stream_id')
        chunk_b64 = data.get('chunk')
        sequence = data.get('sequence', 0)
        is_binary = data.get('is_binary', False)
        
        if not stream_id or not chunk_b64:
            return
            
        try:
            # Decode audio chunk
            if is_binary:
                # For binary frames, chunk_b64 should already be bytes
                chunk_data = chunk_b64 if isinstance(chunk_b64, bytes) else base64.b64decode(chunk_b64)
            else:
                # Traditional base64 JSON format
                chunk_data = base64.b64decode(chunk_b64)
            
            # Add to stream buffer with VAD processing
            success = await self.stream_manager.add_audio_chunk(stream_id, chunk_data, sequence, is_binary)
            
            if not success:
                await self.connection_manager.send_to_client(client_id, {
                    'type': 'audio_stream_error',
                    'stream_id': stream_id,
                    'message': 'Failed to add audio chunk or VAD auto-stop triggered'
                })
                
        except Exception as e:
            logger.error(f"Error handling audio chunk: {e}")
            await self.connection_manager.send_to_client(client_id, {
                'type': 'error',
                'message': f'Audio chunk processing failed: {str(e)}'
            })
            
    async def _handle_end_audio_stream(self, client_id: str, data: Dict):
        """End audio stream and trigger processing"""
        stream_id = data.get('stream_id')
        
        if not stream_id:
            return
            
        success = await self.stream_manager.finalize_stream(stream_id)
        
        await self.connection_manager.send_to_client(client_id, {
            'type': 'audio_stream_ended',
            'stream_id': stream_id,
            'success': success,
            'timestamp': time.time()
        })
        
    async def _handle_text_message(self, client_id: str, data: Dict):
        """Handle text-only message"""
        text = data.get('content', '').strip()
        tts_engine = data.get('tts_engine')
        tts_voice = data.get('tts_voice')
        tts_speed = data.get('tts_speed')
        tts_volume = data.get('tts_volume')
        if any(v is not None for v in [tts_engine, tts_voice, tts_speed, tts_volume]):
            logger.info(
                f"Using dynamic TTS params: engine={tts_engine}, voice={tts_voice}, "
                f"speed={tts_speed}, volume={tts_volume}"
            )
        
        if not text:
            return
            
        llm_text = await self._ask_llm(client_id, text)
        response_text = llm_text or await self.stream_manager._generate_response(text, client_id)
        
        # TTS-Engine bestimmen
        target_engine = None
        if tts_engine:
            t = tts_engine.lower()
            if t == 'piper':
                target_engine = TTSEngineType.PIPER
            elif t == 'kokoro':
                target_engine = TTSEngineType.KOKORO
            elif t == 'zonos':
                target_engine = TTSEngineType.ZONOS

        # Use Staged TTS if enabled, otherwise fallback to single synthesis
        if self.staged_tts.config.enabled and target_engine is None:
            await self._handle_staged_tts_response(client_id, text, response_text)
        else:
            # Traditional single TTS synthesis
            tts_kwargs = {}
            if tts_speed is not None:
                tts_kwargs['speed'] = tts_speed
            if tts_volume is not None:
                tts_kwargs['volume'] = tts_volume
            tts_result = await self.tts_manager.synthesize(
                response_text,
                engine=target_engine,
                voice=tts_voice,
                **tts_kwargs
            )
            
            await self._send_text_response(client_id, {
                'input_text': text,
                'response_text': response_text,
                'audio_data': tts_result.audio_data if tts_result.success else None,
                'tts_engine_used': tts_result.engine_used,
                'tts_voice_used': tts_result.voice_used,
                'tts_success': tts_result.success,
                'tts_error': tts_result.error_message if not tts_result.success else None
            })
    
    async def _handle_staged_tts_response(self, client_id: str, input_text: str, response_text: str):
        """Handle staged TTS response with Piper intro + Zonos main content"""
        sequence_id = None
        try:
            # Process with staged TTS
            canonical_voice = os.getenv("TTS_VOICE", "de-thorsten-low")
            chunks = await self.staged_tts.process_staged_tts(response_text, canonical_voice)

            if not chunks:
                logger.warning("Staged TTS erzeugte keine Chunks")
                await self._send_text_response(client_id, {
                    'input_text': input_text,
                    'response_text': response_text,
                    'audio_data': None,
                    'tts_engine_used': None,
                    'tts_voice_used': None,
                    'tts_success': False,
                    'tts_error': 'no_chunks'
                })
                return

            sequence_id = chunks[0].sequence_id

            first = chunks[0]
            if not (first.success and first.audio_data):
                logger.warning("Piper Intro fehlgeschlagen, – Main-Engine streamt weiter")
                await self._send_text_response(client_id, {
                    'input_text': input_text,
                    'response_text': response_text,
                    'audio_data': None,
                    'tts_engine_used': None,
                    'tts_voice_used': None,
                    'tts_success': False,
                    'tts_error': first.error_message or 'piper_failed'
                })
                end_message = self.staged_tts.create_sequence_end_message(sequence_id)
                await self.connection_manager.send_to_client(client_id, end_message)
                return

            for chunk in chunks:
                if not (chunk.success and chunk.audio_data):
                    continue
                chunk_message = self.staged_tts.create_chunk_message(chunk)
                await self.connection_manager.send_to_client(client_id, chunk_message)
                logger.debug(f"Sent {chunk.engine} chunk {chunk.index}/{chunk.total}")

            end_message = self.staged_tts.create_sequence_end_message(sequence_id)
            await self.connection_manager.send_to_client(client_id, end_message)
            logger.debug(f"Sent sequence end for {sequence_id}")

        except Exception as e:
            logger.error(f"Staged TTS error: {e}")
            await self._fallback_single_tts(
                client_id, input_text, response_text, sequence_id
            )

    async def _fallback_single_tts(
        self,
        client_id: str,
        input_text: str,
        response_text: str,
        sequence_id: str | None = None,
    ):
        """Fallback to single TTS synthesis when staged TTS fails"""
        try:
            tts_result = await self.tts_manager.synthesize(response_text)
            await self._send_text_response(
                client_id,
                {
                    'input_text': input_text,
                    'response_text': response_text,
                    'audio_data': tts_result.audio_data if tts_result.success else None,
                    'tts_engine_used': tts_result.engine_used,
                    'tts_voice_used': getattr(tts_result, 'voice_used', 'default'),
                    'tts_success': tts_result.success,
                    'tts_error': tts_result.error_message if not tts_result.success else None,
                },
            )
            if sequence_id:
                end_message = {
                    'type': 'tts_sequence_end',
                    'sequence_id': sequence_id,
                    'timestamp': time.time(),
                }
                await self.connection_manager.send_to_client(client_id, end_message)
        except Exception as e:
            logger.error(f"Fallback TTS error: {e}")
            # Send error response
            await self.connection_manager.send_to_client(
                client_id,
                {
                    'type': 'error',
                    'code': 'tts_synthesis_failed',
                    'message': 'TTS synthesis failed',
                    'timestamp': time.time(),
                },
            )
        
    async def _handle_switch_tts_engine(self, client_id: str, data: Dict):
        """Handle TTS engine switch request"""
        if not config.enable_engine_switching:
            await self.connection_manager.send_to_client(client_id, {
                'type': 'tts_switch_error',
                'message': 'TTS engine switching is disabled'
            })
            return
            
        engine_name = data.get('engine', '').lower()
        
        # Engine-Type bestimmen
        if engine_name == 'piper':
            target_engine = TTSEngineType.PIPER
        elif engine_name == 'kokoro':
            target_engine = TTSEngineType.KOKORO
        elif engine_name == 'zonos':
            target_engine = TTSEngineType.ZONOS
        else:
            await self.connection_manager.send_to_client(client_id, {
                'type': 'tts_switch_error',
                'message': f'Unknown engine: {engine_name}'
            })
            return
            
        # Engine wechseln
        success = await self.tts_manager.switch_engine(target_engine)
        
        if success:
            self.stats['tts_switches'] += 1
            
            # Update client preferences
            self.connection_manager.connection_info[client_id]['preferred_tts_engine'] = engine_name
            
            await self.connection_manager.send_to_client(client_id, {
                'type': 'tts_engine_switched',
                'engine': engine_name,
                'timestamp': time.time()
            })
        else:
            await self.connection_manager.send_to_client(client_id, {
                'type': 'tts_switch_error',
                'message': f'Failed to switch to {engine_name}'
            })
            
    async def _handle_get_tts_info(self, client_id: str, data: Dict):
        """Handle TTS info request"""
        available_engines = await self.tts_manager.get_available_engines()
        available_voices = await self.tts_manager.get_available_voices()
        current_engine = self.tts_manager.get_current_engine()
        engine_stats = self.tts_manager.get_engine_stats()
        
        # --- Build Kokoro voice labels for GUI (label -> key) ---
        import os as _os
        _kp = _os.getenv("KOKORO_MODEL_PATH", _os.path.join(_os.getenv("TTS_MODEL_DIR", "models"), "kokoro", "kokoro-v1.0.onnx"))
        _kv = _os.getenv("KOKORO_VOICES_PATH", _os.path.join(_os.getenv("TTS_MODEL_DIR", "models"), "kokoro", "voices-v1.0.bin"))
        kokoro_voice_labels = _kokoro_voice_labels(_kv, _kp)

        await self.connection_manager.send_to_client(client_id, {
            'type': 'tts_info',
            'kokoro_voice_labels': kokoro_voice_labels,
            'available_engines': available_engines,
            'available_voices': available_voices,
            'current_engine': current_engine.value if current_engine else None,
            'engine_stats': engine_stats,
            'switching_enabled': config.enable_engine_switching,
            'timestamp': time.time()
        })
        
    async def _handle_set_tts_voice(self, client_id: str, data: Dict):
        """Handle TTS voice change request"""
        voice = data.get('voice')
        engine = data.get('engine')  # Optional: spezifische Engine
        
        if not voice:
            await self.connection_manager.send_to_client(client_id, {
                'type': 'tts_voice_error',
                'message': 'No voice specified'
            })
            return
            
        # Engine bestimmen
        target_engine = None
        if engine:
            if engine.lower() == 'piper':
                target_engine = TTSEngineType.PIPER
            elif engine.lower() == 'kokoro':
                target_engine = TTSEngineType.KOKORO
            elif engine.lower() == 'zonos':
                target_engine = TTSEngineType.ZONOS

        success = await self.tts_manager.set_voice(voice, target_engine)
        
        if success:
            # Update client preferences
            self.connection_manager.connection_info[client_id]['preferred_tts_voice'] = voice
            
            await self.connection_manager.send_to_client(client_id, {
                'type': 'tts_voice_changed',
                'voice': voice,
                'engine': engine or self.tts_manager.get_current_engine().value,
                'timestamp': time.time()
            })
        else:
            await self.connection_manager.send_to_client(client_id, {
                'type': 'tts_voice_error',
                'message': f'Failed to set voice: {voice}'
            })
            
    async def _handle_test_tts_engines(self, client_id: str, data: Dict):
        """Handle TTS engine test request"""
        test_text = data.get('text', 'Test der Sprachsynthese')
        
        results = await self.tts_manager.test_all_engines(test_text)
        
        # Convert results for JSON serialization
        serializable_results = {}
        for engine_name, result in results.items():
            serializable_results[engine_name] = {
                'success': result.success,
                'processing_time_ms': result.processing_time_ms,
                'voice_used': result.voice_used,
                'engine_used': result.engine_used,
                'error_message': result.error_message,
                'audio_length_ms': result.audio_length_ms,
                'sample_rate': result.sample_rate
            }
            
        await self.connection_manager.send_to_client(client_id, {
            'type': 'tts_test_results',
            'results': serializable_results,
            'test_text': test_text,
            'timestamp': time.time()
        })

    async def _handle_get_llm_models(self, client_id: str, data: Dict):
        """Send available LLM models to the client."""
        if self.llm_enabled:
            import logging
            try:
                # LLM Discovery (optional); nutze ENV-URL falls gesetzt
                base = os.getenv("LLM_BASE_URL", "http://127.0.0.1:1234")
                info = await self.llm.list_models(base_url=base) if hasattr(self.llm, "list_models") else {"data":[]}
                self.llm_models = info.get("available", []) or info.get("data", [])
            except Exception as e:
                logging.getLogger(__name__).warning("LLM discovery failed: %s — continuing without LLM list. Set LLM_BASE_URL if needed.", e)
                self.llm_models = []

            loaded = info.get('loaded', [])
        else:
            self.llm_models = []
            loaded = []

        await self.connection_manager.send_to_client(client_id, {
            'type': 'llm_models',
            'available': self.llm_models,
            'loaded': loaded,
            'current': self.llm_model
        })

    async def _handle_switch_llm_model(self, client_id: str, data: Dict):
        """Switch the active LLM model."""
        target = data.get('model')
        ok = False
        if self.llm_enabled and target:
            info = await self.llm.list_models()
            models = info.get('available', [])
            if target in models:
                self.llm_model = target
                self.chat_histories.pop(client_id, None)
                ok = True
        await self.connection_manager.send_to_client(client_id, {
            'type': 'llm_model_switched',
            'ok': ok,
            'current': self.llm_model
        })
        
    async def _handle_ping(self, client_id: str, data: Dict):
        """Handle ping message"""
        current_engine = self.tts_manager.get_current_engine()
        
        await self.connection_manager.send_to_client(client_id, {
            'type': 'pong',
            'timestamp': time.time(),
            'client_timestamp': data.get('timestamp'),
            'current_tts_engine': current_engine.value if current_engine else None
        })
    
    async def _handle_get_stt_models(self, client_id: str, data: Dict):
        """Handle STT models discovery request"""
        try:
            # Available STT models based on hardware capabilities
            available_models = ["tiny", "base", "small", "medium", "large-v2"]
            
            # Detect hardware capabilities
            device_info = {
                "device": config.stt_device,
                "precision": config.stt_precision
            }
            
            # GPU detection for recommendations
            gpu_available = False
            try:
                import torch
                gpu_available = torch.cuda.is_available()
            except ImportError:
                pass
            
            # Hardware-optimized recommendations
            if gpu_available:
                recommended = "base" if config.stt_device == "cuda" else "small"
                fast_models = ["tiny", "base", "small"]
                quality_models = ["small", "medium", "large-v2"]
            else:
                recommended = "tiny"
                fast_models = ["tiny", "base"]
                quality_models = ["base", "small"]
            
            await self.connection_manager.send_to_client(client_id, {
                'type': 'stt_models',
                'available': available_models,
                'current': config.stt_model,
                'recommended': recommended,
                'device_info': device_info,
                'gpu_available': gpu_available,
                'categories': {
                    'fast': fast_models,
                    'quality': quality_models,
                    'gpu_optimized': quality_models if gpu_available else []
                },
                'timestamp': time.time()
            })
            
        except Exception as e:
            logger.error(f"Error getting STT models: {e}")
            await self.connection_manager.send_to_client(client_id, {
                'type': 'error',
                'message': f'Failed to get STT models: {str(e)}',
                'timestamp': time.time()
            })
    
    async def _handle_switch_stt_model(self, client_id: str, data: Dict):
        """Handle STT model switch request"""
        model = data.get('model')
        
        if not model:
            await self.connection_manager.send_to_client(client_id, {
                'type': 'error',
                'message': 'No model specified for STT switch'
            })
            return
        
        try:
            # Note: Hot-swapping STT models requires reinitialization
            # For now, we'll update the config and notify about restart requirement
            old_model = config.stt_model
            config.stt_model = model
            
            # Try hot-swapping the STT engine
            try:
                self.stt_engine.model_size = model
                await self.stt_engine.initialize()
                await self.connection_manager.send_to_client(client_id, {
                    'type': 'stt_model_switched',
                    'old_model': old_model,
                    'new_model': model,
                    'requires_restart': False,
                    'message': f'STT model switched to {model}.',
                    'timestamp': time.time()
                })
            except Exception as exc:
                config.stt_model = old_model
                await self.connection_manager.send_to_client(client_id, {
                    'type': 'stt_model_switch_failed',
                    'old_model': old_model,
                    'new_model': model,
                    'requires_restart': True,
                    'message': f'Switching STT model failed: {exc}. Restart required.',
                    'timestamp': time.time()
                })
            
        except Exception as e:
            logger.error(f"Error switching STT model: {e}")
            await self.connection_manager.send_to_client(client_id, {
                'type': 'error',
                'message': f'Failed to switch STT model: {str(e)}'
            })
    
    async def _handle_set_audio_opts(self, client_id: str, data: Dict):
        """Handle audio options update"""
        try:
            # Extract audio options
            options = {}
            
            if 'noiseSuppression' in data:
                options['noiseSuppression'] = bool(data['noiseSuppression'])
            if 'echoCancellation' in data:
                options['echoCancellation'] = bool(data['echoCancellation'])
            if 'vadEnabled' in data:
                options['vadEnabled'] = bool(data['vadEnabled'])
                # Update global VAD setting
                config.vad_enabled = options['vadEnabled']
            if 'autoStopSec' in data:
                options['autoStopSec'] = float(data['autoStopSec'])
                # Update VAD silence duration
                config.vad_silence_duration_ms = int(options['autoStopSec'] * 1000)
            
            # Store client-specific audio options
            if client_id in self.connection_manager.connection_info:
                if 'audio_options' not in self.connection_manager.connection_info[client_id]:
                    self.connection_manager.connection_info[client_id]['audio_options'] = {}
                self.connection_manager.connection_info[client_id]['audio_options'].update(options)
            
            await self.connection_manager.send_to_client(client_id, {
                'type': 'audio_opts_updated',
                'options': options,
                'message': 'Audio options updated. Changes will apply to new recordings.',
                'timestamp': time.time()
            })
            
        except Exception as e:
            logger.error(f"Error setting audio options: {e}")
            await self.connection_manager.send_to_client(client_id, {
                'type': 'error',
                'message': f'Failed to set audio options: {str(e)}'
            })
    
    async def _handle_set_llm_opts(self, client_id: str, data: Dict):
        """Handle LLM options update"""
        try:
            # Extract and validate LLM options
            if 'temperature' in data:
                temp = float(data['temperature'])
                if 0.0 <= temp <= 2.0:
                    self.llm_temperature = temp
                    
            if 'maxTokens' in data:
                tokens = int(data['maxTokens'])
                if 1 <= tokens <= 4096:
                    self.llm_max_tokens = tokens
                    
            if 'contextTurns' in data:
                turns = int(data['contextTurns'])
                if 1 <= turns <= 20:
                    self.llm_max_turns = turns
            
            # Clear chat history for this client to apply new context settings
            if client_id in self.chat_histories:
                # Keep system message if it exists
                hist = self.chat_histories[client_id]
                system_msg = hist[0] if hist and hist[0].get('role') == 'system' else None
                self.chat_histories[client_id] = [system_msg] if system_msg else []
            
            await self.connection_manager.send_to_client(client_id, {
                'type': 'llm_opts_updated',
                'temperature': self.llm_temperature,
                'maxTokens': self.llm_max_tokens,
                'contextTurns': self.llm_max_turns,
                'message': 'LLM options updated',
                'timestamp': time.time()
            })
            
        except Exception as e:
            logger.error(f"Error setting LLM options: {e}")
            await self.connection_manager.send_to_client(client_id, {
                'type': 'error',
                'message': f'Failed to set LLM options: {str(e)}'
            })
    
    async def _handle_staged_tts_control(self, client_id: str, data: Dict):
        """Handle staged TTS control commands"""
        action = data.get('action', '')
        
        if action == 'toggle':
            # Toggle staged TTS on/off
            self.staged_tts.config.enabled = not self.staged_tts.config.enabled
            await self.connection_manager.send_to_client(client_id, {
                'type': 'staged_tts_status',
                'enabled': self.staged_tts.config.enabled,
                'message': f"Staged TTS {'enabled' if self.staged_tts.config.enabled else 'disabled'}",
                'timestamp': time.time()
            })
            
        elif action == 'clear_cache':
            # Clear TTS cache
            self.staged_tts.clear_cache()
            await self.connection_manager.send_to_client(client_id, {
                'type': 'staged_tts_cache',
                'message': 'Cache cleared',
                'timestamp': time.time()
            })
            
        elif action == 'get_stats':
            # Get staged TTS statistics
            cache_stats = self.staged_tts.get_cache_stats()
            await self.connection_manager.send_to_client(client_id, {
                'type': 'staged_tts_stats',
                'enabled': self.staged_tts.config.enabled,
                'config': {
                    'max_response_length': self.staged_tts.config.max_response_length,
                    'max_intro_length': self.staged_tts.config.max_intro_length,
                    'chunk_timeout_seconds': self.staged_tts.config.chunk_timeout_seconds,
                    'max_chunks': self.staged_tts.config.max_chunks,
                    'enable_caching': self.staged_tts.config.enable_caching
                },
                'cache_stats': cache_stats,
                'timestamp': time.time()
            })
            
        elif action == 'configure':
            # Update configuration
            config_updates = data.get('config', {})
            if 'max_response_length' in config_updates:
                self.staged_tts.config.max_response_length = int(config_updates['max_response_length'])
            if 'max_intro_length' in config_updates:
                self.staged_tts.config.max_intro_length = int(config_updates['max_intro_length'])
            if 'chunk_timeout_seconds' in config_updates:
                self.staged_tts.config.chunk_timeout_seconds = int(config_updates['chunk_timeout_seconds'])
            if 'max_chunks' in config_updates:
                self.staged_tts.config.max_chunks = int(config_updates['max_chunks'])
            if 'enable_caching' in config_updates:
                self.staged_tts.config.enable_caching = bool(config_updates['enable_caching'])
                
            await self.connection_manager.send_to_client(client_id, {
                'type': 'staged_tts_config_updated',
                'config': {
                    'max_response_length': self.staged_tts.config.max_response_length,
                    'max_intro_length': self.staged_tts.config.max_intro_length,
                    'chunk_timeout_seconds': self.staged_tts.config.chunk_timeout_seconds,
                    'max_chunks': self.staged_tts.config.max_chunks,
                    'enable_caching': self.staged_tts.config.enable_caching
                },
                'timestamp': time.time()
            })
        
        else:
            await self.connection_manager.send_to_client(client_id, {
                'type': 'error',
                'message': f'Unknown staged TTS action: {action}',
                'timestamp': time.time()
            })
        
    async def _send_audio_response(self, client_id: str, response_data: Dict):
        """Send response from audio processing"""
        # Encode audio if present
        if response_data.get('audio_data'):
            audio_b64 = base64.b64encode(response_data['audio_data']).decode('utf-8')
        else:
            audio_b64 = None
            
        await self.connection_manager.send_to_client(client_id, {
            'type': 'response',
            'transcription': response_data.get('transcription'),
            'content': response_data.get('response_text'),
            'audio': f"data:audio/wav;base64,{audio_b64}" if audio_b64 else None,
            'processing_time_ms': response_data.get('processing_time_ms'),
            'tts_engine_used': response_data.get('tts_engine_used'),
            'tts_voice_used': response_data.get('tts_voice_used'),
            'tts_success': response_data.get('tts_success'),
            'tts_error': response_data.get('tts_error'),
            'timestamp': time.time()
        })
        
    async def _send_text_response(self, client_id: str, response_data: Dict):
        """Send response from text processing"""
        # Encode audio if present
        if response_data.get('audio_data'):
            audio_b64 = base64.b64encode(response_data['audio_data']).decode('utf-8')
        else:
            audio_b64 = None
            
        await self.connection_manager.send_to_client(client_id, {
            'type': 'response',
            'content': response_data.get('response_text'),
            'audio': f"data:audio/wav;base64,{audio_b64}" if audio_b64 else None,
            'tts_engine_used': response_data.get('tts_engine_used'),
            'tts_voice_used': response_data.get('tts_voice_used'),
            'tts_success': response_data.get('tts_success'),
            'tts_error': response_data.get('tts_error'),
            'timestamp': time.time()
        })
        
    def get_stats(self) -> Dict:
        """Get server statistics"""
        return {
            'active_connections': len(self.connection_manager.active_connections),
            'total_connections': self.stats['connections'],
            'messages_processed': self.stats['messages_processed'],
            'audio_streams_processed': self.stats['audio_streams'],
            'tts_engine_switches': self.stats['tts_switches'],
            'avg_stt_latency_ms': sum(self.stats['stt_latency_ms']) / len(self.stats['stt_latency_ms']) if self.stats['stt_latency_ms'] else 0,
            'avg_tts_latency_ms': sum(self.stats['tts_latency_ms']) / len(self.stats['tts_latency_ms']) if self.stats['tts_latency_ms'] else 0,
            'uptime_seconds': time.time() - self.stats['start_time'],
            'active_audio_streams': len(self.stream_manager.active_streams),
            'processing_queue_size': self.stream_manager.processing_queue.qsize(),
            'tts_engines': self.tts_manager.get_engine_stats()
        }

# Main server instance
server = VoiceServer()

async def main():
    """Main server entry point with improved error handling"""
    metrics_runner = None
    
    try:
        # Initialize server with detailed logging
        logger.info("🔧 Starting server initialization...")
        await server.initialize()
        logger.info("✅ Server initialization completed")
        
        # Start HTTP Metrics API with better error handling
        logger.info(f"🌐 Starting Metrics API on port {config.metrics_port}...")
        try:
            metrics_runner = await start_metrics_api(server, port=config.metrics_port)
            logger.info(f"✅ Metrics API started successfully on port {config.metrics_port}")
        except Exception as e:
            logger.error(f"❌ Failed to start metrics API: {e}")
            import traceback
            logger.error(f"Metrics API traceback:\n{traceback.format_exc()}")
            # Continue without metrics API
            metrics_runner = None
        
        # Start WebSocket server with better error handling
        logger.info(f"🔗 Starting WebSocket server on {WS_HOST}:{WS_PORT}...")
        
        try:
            async with websockets.serve(
                server.handle_websocket,
                WS_HOST, WS_PORT,
                close_timeout=10,
                ping_interval=config.ping_interval,
                ping_timeout=config.ping_timeout
            ):
                logger.info("🚀 Voice Server with TTS switching is running!")
                logger.info(f"🔗 WebSocket server: ws://{WS_HOST}:{WS_PORT}")
                if metrics_runner:
                    logger.info(f"📊 Metrics available at: http://{WS_HOST}:{config.metrics_port}/metrics")
                    logger.info(f"🏥 Health check at: http://{WS_HOST}:{config.metrics_port}/health")
                else:
                    logger.warning("⚠️  Metrics API not available")
                logger.info("🎙️  TTS Engine switching enabled" if config.enable_engine_switching else "🎙️  TTS Engine switching disabled")
                logger.info("✨ Server startup completed successfully!")
                
                # Run forever
                await asyncio.Future()
                
        except Exception as ws_error:
            logger.error(f"❌ WebSocket server error: {ws_error}")
            import traceback
            logger.error(f"WebSocket traceback:\n{traceback.format_exc()}")
            raise
            
    except Exception as e:
        logger.error(f"❌ Server startup failed: {e}")
        import traceback
        logger.error(f"Startup traceback:\n{traceback.format_exc()}")
        raise
        
    finally:
        # Cleanup
        logger.info("🧹 Starting cleanup...")
        try:
            if metrics_runner:
                logger.info("Stopping metrics API...")
                await metrics_runner.cleanup()
        except Exception as e:
            logger.error(f"Metrics cleanup error: {e}")
            
        try:
            logger.info("Stopping TTS manager...")
            await server.tts_manager.cleanup()
        except Exception as e:
            logger.error(f"TTS cleanup error: {e}")
            
        logger.info("🏁 Cleanup completed")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
