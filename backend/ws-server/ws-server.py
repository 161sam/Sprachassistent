#!/usr/bin/env python3
"""Unified WebSocket Audio Streaming Server.

This server consolidates all historic implementations into a single, modern
code base.  It combines low latency audio streaming, real-time STT processing
and runtime switching between Piper and Kokoro TTS engines.  Legacy files
have been moved to ``archive/`` (`ws-server-pre-tts.py`,
`ws-server-old.py`).

Features integrated from previous versions:

* Environment based configuration
* STT audio pre-processing (``numpy``/``soundfile``)
* Intent routing with optional Flowise/n8n calls (``aiohttp``)
* Optional debug file saving (``aiofiles``)
* Metrics API and TTS engine switching

TODO:
    - Modularize TTS engine switching
    - Implement authentication/token handling

"""

import asyncio
import websockets
import json
import base64
import time
import uuid
import numpy as np
import os
import logging
import io
from datetime import datetime
from typing import Dict, Optional, List, AsyncGenerator
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
from collections import deque
import aiohttp
import aiofiles
import soundfile as sf
from faster_whisper import WhisperModel
from pathlib import Path

# Importiere neues TTS-System
from .tts import TTSManager, TTSEngineType, TTSConfig

from metrics_api import start_metrics_api
from skills import load_all_skills
from intent_classifier import IntentClassifier

# Enhanced configuration
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
    ws_port: int = int(os.getenv("WS_PORT", 8123))
    metrics_port: int = int(os.getenv("METRICS_PORT", 8124))

    # Models
    stt_model: str = os.getenv("STT_MODEL", "base")
    stt_device: str = os.getenv("STT_DEVICE", "cpu")
    stt_precision: str = os.getenv("STT_PRECISION", "int8")

    # TTS Configuration
    default_tts_engine: str = os.getenv("DEFAULT_TTS_ENGINE", "piper")  # "piper" or "kokoro"
    enable_engine_switching: bool = os.getenv("ENABLE_TTS_SWITCHING", "true").lower() == "true"

    # External services
    flowise_url: str = os.getenv("FLOWISE_URL", "")
    flowise_id: str = os.getenv("FLOWISE_ID", "")
    n8n_url: str = os.getenv("N8N_URL", "")
    flowise_api_key: str = os.getenv("FLOWISE_API_KEY", "")

    # Retry configuration for external services
    retry_limit: int = int(os.getenv("RETRY_LIMIT", 3))
    retry_backoff: float = float(os.getenv("RETRY_BACKOFF", 1.0))

    # Skills and ML
    enabled_skills: List[str] = field(
        default_factory=lambda: [s.strip() for s in os.getenv("ENABLED_SKILLS", "").split(",") if s.strip()]
    )
    intent_model: str = os.getenv("INTENT_MODEL", "models/intent_classifier.bin")

    # Debugging
    save_debug_audio: bool = os.getenv("SAVE_DEBUG_AUDIO", "false").lower() == "true"

config = StreamingConfig()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AudioChunk:
    """Optimized audio chunk representation"""
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

    def __init__(self, model_size: str = "base", device: str = "cpu", workers: int = 2):
        self.model_size = model_size
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
        return WhisperModel(
            self.model_size, 
            device=self.device, 
            compute_type=config.stt_precision
        )
        
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
        """Normalize and resample audio bytes for STT."""
        audio_buf = io.BytesIO(audio_bytes)
        data, sr = sf.read(audio_buf, dtype="float32")

        # Resample if necessary
        if sr != config.sample_rate:
            duration = data.shape[0] / sr
            target_length = int(duration * config.sample_rate)
            data = np.interp(
                np.linspace(0, data.shape[0], target_length),
                np.arange(data.shape[0]),
                data,
            )

        # Simple normalization
        max_val = np.max(np.abs(data))
        if max_val > 0:
            data = data / max_val

        return data.astype(np.float32)

    def _transcribe_sync(self, audio_array: np.ndarray) -> str:
        """Synchronous transcription in worker thread."""
        try:
            segments, info = self.model.transcribe(audio_array, sample_rate=config.sample_rate)
            text = "".join(segment.text for segment in segments).strip()
            return text or "(no speech detected)"
        except Exception as e:
            logger.error(f"Sync transcription error: {e}")
            return f"[Transcription failed: {str(e)}]"

class AudioStreamManager:
    """Manages real-time audio streams with minimal latency"""
    
    def __init__(self, stt_engine: AsyncSTTEngine, tts_manager: TTSManager):
        self.stt_engine = stt_engine
        self.tts_manager = tts_manager
        self.active_streams: Dict[str, Dict] = {}
        self.processing_queue = asyncio.Queue(maxsize=1000)
        self.response_callbacks: Dict[str, callable] = {}

        # Skills und Intent-Klassifizierer laden
        skills_path = Path(__file__).parent / "skills"
        self.skills = load_all_skills(skills_path, config.enabled_skills)
        if config.enabled_skills:
            logger.info("Aktive Skills: %s", ", ".join(type(s).__name__ for s in self.skills))
        self.intent_classifier = IntentClassifier(config.intent_model)

        # Start background processor
        asyncio.create_task(self._process_audio_queue())
        
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
            'tts_voice': None    # Client-spezifische Stimme
        }
        
        self.response_callbacks[stream_id] = response_callback
        logger.debug(f"Started audio stream {stream_id} for client {client_id}")
        
        return stream_id
        
    async def add_audio_chunk(self, stream_id: str, chunk_data: bytes, sequence: int) -> bool:
        """Add audio chunk to stream buffer"""
        if stream_id not in self.active_streams:
            return False
            
        stream = self.active_streams[stream_id]
        
        # Check if stream is still valid
        if not stream['is_active']:
            return False
            
        # Check duration limit
        if time.time() - stream['start_time'] > config.max_audio_duration:
            logger.warning(f"Stream {stream_id} exceeded max duration")
            return False
            
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
                    'tts_voice': stream.get('tts_voice')
                })
                logger.debug(f"Queued stream {stream_id} for processing ({len(audio_data)} bytes)")
                return True
            except asyncio.QueueFull:
                logger.error(f"Processing queue full, dropping stream {stream_id}")
                return False
        else:
            logger.warning(f"No audio data in finalized stream {stream_id}")
            return False
            
    async def set_stream_tts_config(self, stream_id: str, engine: Optional[str] = None, voice: Optional[str] = None):
        """Setze TTS-Konfiguration für Stream"""
        if stream_id in self.active_streams:
            if engine:
                self.active_streams[stream_id]['tts_engine'] = engine
            if voice:
                self.active_streams[stream_id]['tts_voice'] = voice
                
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
        
        try:
            start_time = time.time()

            # Transcribe audio
            transcription = await self.stt_engine.transcribe_audio(audio_data)
            
            # Generate response (simplified - would include intent routing)
            response_text = await self._generate_response(transcription, client_id)
            
            # TTS-Engine bestimmen
            target_engine = None
            if tts_engine:
                if tts_engine.lower() == "piper":
                    target_engine = TTSEngineType.PIPER
                elif tts_engine.lower() == "kokoro":
                    target_engine = TTSEngineType.KOKORO
                    
            # Generate TTS audio mit spezifizierter Engine
            tts_result = await self.tts_manager.synthesize(
                response_text,
                engine=target_engine,
                voice=tts_voice
            )

            # Optional debug: save audio files asynchronously
            if config.save_debug_audio:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                try:
                    async with aiofiles.open(f"debug_in_{timestamp}.wav", "wb") as f_in:
                        await f_in.write(audio_data)
                    if tts_result.success and tts_result.audio_data:
                        async with aiofiles.open(f"debug_out_{timestamp}.wav", "wb") as f_out:
                            await f_out.write(tts_result.audio_data)
                except Exception as dbg_err:
                    logger.debug(f"Failed to write debug audio: {dbg_err}")
            
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
                
    async def _generate_response(self, transcription: str, client_id: str) -> str:
        """Generate response using Skills, ML classification and external routing."""
        if not transcription or transcription.startswith('['):
            return "Entschuldigung, ich konnte Sie nicht verstehen."

        text = transcription.lower().strip()

        intent = self.intent_classifier.classify(text)

        if intent == "external_request":
            external = await self._route_external(text, client_id)
            if external:
                return external

        for skill in self.skills:
            if getattr(skill, "intent_name", None) == intent:
                return skill.handle(text)

        for skill in self.skills:
            if skill.can_handle(text):
                return skill.handle(text)

        return "Entschuldigung, dafür habe ich keine Antwort."

    async def _route_external(self, text: str, client_id: str) -> Optional[str]:
        if config.flowise_url and config.flowise_id:
            return await self._ask_flowise(text, client_id)
        if config.n8n_url:
            return await self._trigger_n8n(text, client_id)
        return None

    async def _ask_flowise(self, query: str, client_id: str) -> str:
        """Send query to Flowise REST API."""
        url = f"{config.flowise_url}/api/v1/prediction/{config.flowise_id}"
        headers = {"Content-Type": "application/json"}
        if config.flowise_api_key:
            headers["Authorization"] = f"Bearer {config.flowise_api_key}"
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
        return "(keine Antwort von Flowise)"

    async def _trigger_n8n(self, query: str, client_id: str) -> str:
        """Trigger n8n webhook with the given query."""
        payload = {"query": query, "sessionId": client_id}
        for attempt in range(1, config.retry_limit + 1):
            try:
                timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(config.n8n_url, json=payload) as resp:
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
    
    def __init__(self, stream_manager: AudioStreamManager, tts_manager: TTSManager):
        self.active_connections: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.connection_info: Dict[str, Dict] = {}
        self.stream_manager = stream_manager
        self.tts_manager = tts_manager
        
    async def register(self, websocket: websockets.WebSocketServerProtocol) -> str:
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
            'preferred_tts_voice': None
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
            return False

class OptimizedVoiceServer:
    """Main server with optimized audio streaming and TTS switching"""
    
    def __init__(self):
        self.stt_engine = AsyncSTTEngine(
            model_size=config.stt_model,
            device=config.stt_device,
            workers=config.stt_workers
        )
        
        # Initialisiere TTS-Manager
        self.tts_manager = TTSManager()
        
        self.stream_manager = AudioStreamManager(self.stt_engine, self.tts_manager)
        self.connection_manager = ConnectionManager(self.stream_manager, self.tts_manager)
        
        # Performance metrics
        self.stats = {
            'connections': 0,
            'messages_processed': 0,
            'audio_streams': 0,
            'tts_switches': 0,
            'start_time': time.time()
        }
        
    async def initialize(self):
        """Initialize all components"""
        logger.info("Initializing optimized voice server with TTS switching...")
        
        # Initialize STT engine
        await self.stt_engine.initialize()
        
        # Initialize TTS Manager
        # Standard-Konfigurationen für beide Engines
        piper_config = TTSConfig(
            engine_type="piper",
            model_path="",  # Wird automatisch ermittelt
            voice="de-thorsten-low",
            speed=1.0,
            language="de",
            sample_rate=22050
        )
        
        kokoro_config = TTSConfig(
            engine_type="kokoro",
            model_path="",  # Wird automatisch ermittelt
            voice="af_sarah",
            speed=1.0,
            language="en",
            sample_rate=24000
        )
        
        # Bestimme Standard-Engine
        default_engine = TTSEngineType.PIPER if config.default_tts_engine.lower() == "piper" else TTSEngineType.KOKORO
        
        success = await self.tts_manager.initialize(piper_config, kokoro_config, default_engine)
        if not success:
            logger.error("TTS-Manager Initialisierung fehlgeschlagen!")
            
        logger.info("Voice server initialized successfully")
        
    async def handle_websocket(self, websocket, path):
        """Handle WebSocket connection with optimized message processing"""
        client_id = await self.connection_manager.register(websocket)
        
        try:
            # Send welcome message with TTS info
            available_engines = await self.tts_manager.get_available_engines()
            current_engine = self.tts_manager.get_current_engine()
            
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
                    'current_engine': current_engine.value if current_engine else None,
                    'switching_enabled': config.enable_engine_switching
                }
            })
            
            # Message handling loop
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(client_id, data)

                    # Update stats
                    self.connection_manager.connection_info[client_id]['messages_received'] += 1
                    self.connection_manager.connection_info[client_id]['last_activity'] = time.time()
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

        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"Client {client_id} connection closed: {e.code} {e.reason}")
        except Exception:
            logging.exception(f"WebSocket error for {client_id}")
            try:
                await websocket.close(code=1011, reason="server error")
            except Exception:
                pass
        finally:
            await self.connection_manager.unregister(client_id)
            
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
        
        # Create response callback
        async def response_callback(response_data):
            await self._send_audio_response(client_id, response_data)
            
        stream_id = await self.stream_manager.start_stream(client_id, response_callback)
        
        # TTS-Konfiguration für Stream setzen
        await self.stream_manager.set_stream_tts_config(stream_id, tts_engine, tts_voice)
        
        await self.connection_manager.send_to_client(client_id, {
            'type': 'audio_stream_started',
            'stream_id': stream_id,
            'tts_engine': tts_engine,
            'tts_voice': tts_voice,
            'timestamp': time.time()
        })
        
        self.stats['audio_streams'] += 1
        
    async def _handle_audio_chunk(self, client_id: str, data: Dict):
        """Handle incoming audio chunk"""
        stream_id = data.get('stream_id')
        chunk_b64 = data.get('chunk')
        sequence = data.get('sequence', 0)
        
        if not stream_id or not chunk_b64:
            return
            
        try:
            # Decode audio chunk
            chunk_data = base64.b64decode(chunk_b64)
            
            # Add to stream buffer
            success = await self.stream_manager.add_audio_chunk(stream_id, chunk_data, sequence)
            
            if not success:
                await self.connection_manager.send_to_client(client_id, {
                    'type': 'audio_stream_error',
                    'stream_id': stream_id,
                    'message': 'Failed to add audio chunk'
                })
                
        except Exception as e:
            logger.error(f"Error handling audio chunk: {e}")
            
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
        
        if not text:
            return
            
        # Generate response
        response_text = await self.stream_manager._generate_response(text, client_id)
        
        # TTS-Engine bestimmen
        target_engine = None
        if tts_engine:
            if tts_engine.lower() == "piper":
                target_engine = TTSEngineType.PIPER
            elif tts_engine.lower() == "kokoro":
                target_engine = TTSEngineType.KOKORO
                
        # Generate TTS
        tts_result = await self.tts_manager.synthesize(
            response_text, 
            engine=target_engine,
            voice=tts_voice
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
        
        await self.connection_manager.send_to_client(client_id, {
            'type': 'tts_info',
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
        
    async def _handle_ping(self, client_id: str, data: Dict):
        """Handle ping message"""
        current_engine = self.tts_manager.get_current_engine()
        
        await self.connection_manager.send_to_client(client_id, {
            'type': 'pong',
            'timestamp': time.time(),
            'client_timestamp': data.get('timestamp'),
            'current_tts_engine': current_engine.value if current_engine else None
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
            'uptime_seconds': time.time() - self.stats['start_time'],
            'active_audio_streams': len(self.stream_manager.active_streams),
            'processing_queue_size': self.stream_manager.processing_queue.qsize(),
            'tts_engines': self.tts_manager.get_engine_stats()
        }

# Main server instance
server = OptimizedVoiceServer()

async def main():
    """Main server entry point"""
    # Initialize server
    await server.initialize()
    
    # Start HTTP Metrics API
    try:
        metrics_runner = await start_metrics_api(server, port=config.metrics_port)
        logger.info(f"📊 Metrics API started on port {config.metrics_port}")
    except Exception as e:
        logger.warning(f"Failed to start metrics API: {e}")
        metrics_runner = None
    
    # Start WebSocket server
    logger.info(f"Starting optimized WebSocket server with TTS switching on port {config.ws_port}")
    
    try:
        async with websockets.serve(
            server.handle_websocket,
            "0.0.0.0",
            config.ws_port,
            max_size=10_000_000,  # 10MB max message size
            ping_interval=config.ping_interval,
            ping_timeout=config.ping_timeout,
            close_timeout=10
        ):
            logger.info("🚀 Optimized Voice Server with TTS switching is running!")
            logger.info(f"📊 Metrics available at: http://localhost:{config.metrics_port}/metrics")
            logger.info(f"🏥 Health check at: http://localhost:{config.metrics_port}/health")
            logger.info("🎙️  TTS Engine switching enabled" if config.enable_engine_switching else "🎙️  TTS Engine switching disabled")
            await asyncio.Future()  # Run forever
    finally:
        if metrics_runner:
            await metrics_runner.cleanup()
        await server.tts_manager.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
