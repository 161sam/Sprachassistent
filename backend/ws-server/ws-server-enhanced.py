#!/usr/bin/env python3
"""
Enhanced Voice Assistant WebSocket Server
Now with Binary Audio Support while maintaining backwards compatibility
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
from datetime import datetime
from typing import Dict, Optional, List, AsyncGenerator
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
from collections import deque
import aiohttp
import aiofiles
from faster_whisper import WhisperModel
from pathlib import Path
from dotenv import load_dotenv

# Binary Audio Support - Import enhanced components
try:
    from binary_audio_handler import WebSocketBinaryRouter, BinaryAudioHandler
    from enhanced_websocket_server import EnhancedWebSocketServer
    from performance_metrics import MetricsIntegratedWebSocketServer
    BINARY_AUDIO_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("✅ Binary audio components loaded successfully")
except ImportError as e:
    BINARY_AUDIO_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning(f"⚠️  Binary audio components not available: {e}")
    logger.info("🔄 Running in legacy JSON-only mode")

# --- PYTHONPATH bootstrap (project root) ---
import sys as _sys
from pathlib import Path as _P
_PROJECT_ROOT = _P(__file__).resolve().parents[2]
(_sys.path.insert(0, str(_PROJECT_ROOT))
 if str(_PROJECT_ROOT) not in _sys.path else None)
# ------------------------------------------

# Original imports
from backend.tts import TTSManager, TTSEngineType, TTSConfig
from staged_tts import StagedTTSProcessor
from staged_tts.staged_processor import StagedTTSConfig
from audio.vad import VoiceActivityDetector, VADConfig, create_vad_processor
from auth.token_utils import verify_token

# Load environment variables
load_dotenv('.env.defaults', override=False)
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import original components
try:
    from intent_classifier import IntentClassifier
except ImportError as e:
    logger.warning(f"Intent classifier not available: {e}")
    class IntentClassifier:
        def __init__(self, *args, **kwargs):
            pass
        def classify(self, text):
            return type('obj', (object,), {'intent': 'unknown', 'confidence': 0.0})

try:
    from skills import load_all_skills
except ImportError as e:
    logger.warning(f"Skills module not available: {e}")
    def load_all_skills(*args, **kwargs):
        return []

try:
    from metrics_api import start_metrics_api
except ImportError as e:
    logger.error(f"Metrics API not available: {e}")
    async def start_metrics_api(*args, **kwargs):
        raise ImportError("Metrics API module not available")

# Configuration with binary audio support
WS_HOST = os.getenv('WS_HOST','127.0.0.1')
WS_PORT = int(os.getenv('WS_PORT','48231'))

@dataclass
class StreamingConfig:
    """Enhanced configuration with binary audio support."""

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

    # Local LLM
    llm_enabled: bool = os.getenv("LLM_ENABLED", "true").lower() == "true"
    llm_api_base: str = os.getenv("LLM_API_BASE", "")
    llm_default_model: str = os.getenv("LLM_DEFAULT_MODEL", "auto")
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", 0.7))
    llm_max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", 256))

    # Skills and ML
    enabled_skills: List[str] = field(
        default_factory=lambda: [s.strip() for s in os.getenv("ENABLED_SKILLS", "").split(",") if s.strip()]
    )
    intent_model: str = os.getenv("INTENT_MODEL", "models/intent_classifier.bin")

    # Debugging
    save_debug_audio: bool = os.getenv("SAVE_DEBUG_AUDIO", "false").lower() == "true"
    
    # Staged TTS Configuration
    staged_tts_enabled: bool = os.getenv("STAGED_TTS_ENABLED", "true").lower() == "true"
    staged_tts_max_response_length: int = int(os.getenv("STAGED_TTS_MAX_RESPONSE_LENGTH", "500"))
    staged_tts_max_intro_length: int = int(os.getenv("STAGED_TTS_MAX_INTRO_LENGTH", "120"))
    staged_tts_chunk_timeout: int = int(os.getenv("STAGED_TTS_CHUNK_TIMEOUT", "10"))
    staged_tts_max_chunks: int = int(os.getenv("STAGED_TTS_MAX_CHUNKS", "3"))
    staged_tts_enable_caching: bool = os.getenv("STAGED_TTS_ENABLE_CACHING", "true").lower() == "true"
    
    # VAD Configuration
    vad_enabled: bool = os.getenv("VAD_ENABLED", "false").lower() == "true"
    vad_silence_duration_ms: int = int(os.getenv("VAD_SILENCE_DURATION_MS", "1500"))
    vad_energy_threshold: float = float(os.getenv("VAD_ENERGY_THRESHOLD", "0.01"))
    vad_min_speech_duration_ms: int = int(os.getenv("VAD_MIN_SPEECH_DURATION_MS", "500"))
    
    # Binary Audio Support (NEW)
    enable_binary_audio: bool = os.getenv("ENABLE_BINARY_AUDIO", "true").lower() == "true" and BINARY_AUDIO_AVAILABLE
    enable_http_metrics: bool = os.getenv("ENABLE_HTTP_METRICS", "false").lower() == "true"
    vad_threshold: float = float(os.getenv("VAD_THRESHOLD", "0.02"))
    vad_silence_duration: float = float(os.getenv("VAD_SILENCE_DURATION", "1.0"))
    max_concurrent_streams: int = int(os.getenv("MAX_CONCURRENT_STREAMS", "10"))
    audio_buffer_size: int = int(os.getenv("AUDIO_BUFFER_SIZE", "4096"))

config = StreamingConfig()

# Log binary audio status
if config.enable_binary_audio:
    logger.info("🎵 Binary Audio Protocol: ENABLED (Protocol v2.0)")
    logger.info("📊 Performance metrics: ENABLED")
    logger.info("🎙️ Voice Activity Detection: ENABLED")
    logger.info("🔄 Backwards compatibility: ENABLED")
else:
    logger.info("🎵 Binary Audio Protocol: DISABLED (JSON-only mode)")
    logger.info("🔄 Running in legacy compatibility mode")

ALLOWED_IPS: List[str] = [ip.strip() for ip in os.getenv("ALLOWED_IPS", "").split(",") if ip.strip()]

# Import original VoiceServer if available
try:
    # Try to import from existing ws-server module
    import importlib.util
    spec = importlib.util.spec_from_file_location("ws_server", "/home/saschi/Sprachassistent/backend/ws-server/ws-server.py")
    ws_server_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ws_server_module)
    VoiceServer = ws_server_module.VoiceServer
    VOICE_SERVER_AVAILABLE = True
except (ImportError, AttributeError, FileNotFoundError):
    logger.warning("Original VoiceServer not available, using minimal implementation")
    VOICE_SERVER_AVAILABLE = False
    
    # Minimal VoiceServer for testing
    class VoiceServer:
        def __init__(self):
            self.stats = {'start_time': time.time()}
            # Add mock components for enhanced server compatibility
            self.stt_engine = None
            self.tts_manager = MockTTSManager()
            self.connections = {}
            logger.info("🔄 Minimal VoiceServer initialized")
        
        async def initialize(self):
            if self.tts_manager:
                await self.tts_manager.initialize()
            logger.info("✅ Minimal VoiceServer components initialized")
            
        def get_stats(self):
            return {
                **self.stats,
                'active_connections': len(self.connections),
                'uptime': time.time() - self.stats['start_time']
            }
        
        async def handle_websocket(self, websocket, path=None):
            """Basic WebSocket handler"""
            client_id = str(uuid.uuid4())[:8]
            self.connections[client_id] = websocket
            logger.info(f"🔗 Client {client_id} connected")
            
            try:
                await websocket.send(json.dumps({
                    'type': 'server_info',
                    'binary_audio_enabled': config.enable_binary_audio,
                    'timestamp': time.time()
                }))
                
                async for message in websocket:
                    if isinstance(message, str):
                        data = json.loads(message)
                        if data.get('type') == 'ping':
                            await websocket.send(json.dumps({
                                'type': 'pong',
                                'timestamp': time.time()
                            }))
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
            finally:
                if client_id in self.connections:
                    del self.connections[client_id]
                logger.info(f"📱 Client {client_id} disconnected")

    class MockTTSManager:
        """Mock TTS manager for compatibility"""
        def __init__(self):
            pass
        
        async def initialize(self, *args, **kwargs):
            return True
        
        async def cleanup(self):
            pass

# Enhanced server with binary support
if BINARY_AUDIO_AVAILABLE and config.enable_binary_audio:
    logger.info("🚀 Initializing Enhanced WebSocket Server with Binary Audio Support")
    
    class EnhancedVoiceServer(VoiceServer):
        """Enhanced server with binary audio capabilities"""
        
        def __init__(self):
            super().__init__()
            
            # Initialize enhanced WebSocket server
            self.enhanced_server = EnhancedWebSocketServer(
                self.stt_engine,
                self.tts_manager,
                config
            )
            
            # Add performance metrics
            if config.enable_http_metrics:
                self.metrics_server = MetricsIntegratedWebSocketServer(self.enhanced_server)
                logger.info("📊 Performance metrics integration: ENABLED")
            else:
                self.metrics_server = None
                logger.info("📊 Performance metrics integration: DISABLED")
        
        async def handle_websocket(self, websocket, path=None):
            """Enhanced WebSocket handler with binary support"""
            try:
                # Use enhanced server's handler
                await self.enhanced_server.handle_client(websocket, path or '/')
            except Exception as e:
                logger.error(f"Enhanced WebSocket handler error: {e}")
                # Fallback to original handler
                await super().handle_websocket(websocket, path)
        
        def get_enhanced_stats(self):
            """Get comprehensive stats including binary metrics"""
            base_stats = super().get_stats()
            
            if self.metrics_server:
                enhanced_stats = self.metrics_server.get_metrics_summary()
                return {**base_stats, **enhanced_stats}
            
            return {
                **base_stats,
                'binary_audio_enabled': True,
                'protocol_version': '2.0'
            }
    
        # Use enhanced server
    VoiceServer = EnhancedVoiceServer
    logger.info("✅ Enhanced Voice Server with Binary Audio initialized")

else:
    if not VOICE_SERVER_AVAILABLE:
        logger.info("🔄 Using Minimal Voice Server (Testing mode)")
    else:
        logger.info("🔄 Using Legacy Voice Server (JSON-only)")

# Initialize the server
server = VoiceServer()

async def main():
    """Enhanced main function with binary audio support"""
    metrics_runner = None
    
    try:
        # Display startup banner
        print("\n" + "=" * 60)
        print("🎤 Voice Assistant Backend Starting...")
        if config.enable_binary_audio:
            print("🎵 Binary Audio Protocol v2.0: ENABLED")
            print("📊 Performance Metrics: ENABLED")
            print("🎙️ Voice Activity Detection: ENABLED")
            print("🔄 Backwards Compatibility: ENABLED")
        else:
            print("🔄 Legacy JSON Protocol: ENABLED")
        print("=" * 60)
        
        # Initialize server
        logger.info("🔧 Starting server initialization...")
        await server.initialize()
        logger.info("✅ Server initialization completed")
        
        # Start HTTP Metrics API if available and enabled
        if config.enable_http_metrics:
            logger.info(f"🌐 Starting Metrics API on port {config.metrics_port}...")
            try:
                metrics_runner = await start_metrics_api(server, port=config.metrics_port)
                logger.info(f"✅ Metrics API started successfully on port {config.metrics_port}")
            except Exception as e:
                logger.error(f"❌ Failed to start metrics API: {e}")
                metrics_runner = None
        
        # Start WebSocket server
        logger.info(f"🔗 Starting WebSocket server on {WS_HOST}:{WS_PORT}...")
        
        # Enhanced WebSocket server configuration
        websocket_config = {
            'close_timeout': 10,
            'ping_interval': config.ping_interval,
            'ping_timeout': config.ping_timeout,
            'max_size': 10**7,  # 10MB max message size for binary frames
        }
        
        # Disable compression for binary frames
        if config.enable_binary_audio:
            websocket_config['compression'] = None
            logger.info("🎵 Binary frame support: Compression disabled for optimal performance")
        
        async with websockets.serve(
            server.handle_websocket,
            WS_HOST, WS_PORT,
            **websocket_config
        ):
            print("\n" + "=" * 60)
            print("🚀 Voice Assistant Server is running!")
            print(f"🔗 WebSocket: ws://{WS_HOST}:{WS_PORT}")
            if config.enable_binary_audio:
                print("🎵 Binary Audio Protocol v2.0: ACTIVE")
                print("📊 Performance Monitoring: ACTIVE")
            if metrics_runner:
                print(f"📊 Metrics API: http://{WS_HOST}:{config.metrics_port}/metrics")
                print(f"🏥 Health Check: http://{WS_HOST}:{config.metrics_port}/health")
            print("🎙️ TTS Engine switching:", "ENABLED" if config.enable_engine_switching else "DISABLED")
            print("🎭 Staged TTS:", "ENABLED" if config.staged_tts_enabled else "DISABLED")
            print("🔄 Press Ctrl+C to stop")
            print("=" * 60)
            
            # Run forever
            await asyncio.Future()
                
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
        print("\n🛑 Server stopped by user")
        logger.info("Server shutdown requested")
    except Exception as e:
        print(f"💥 Server error: {e}")
        logger.error(f"Server error: {e}")
        raise
