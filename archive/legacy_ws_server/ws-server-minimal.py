#!/usr/bin/env python3
"""
Enhanced Voice Assistant WebSocket Server - Standalone Version
Binary Audio Support with full backwards compatibility
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
from typing import Dict, Optional, List
from dataclasses import dataclass, field
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

# Load environment variables
load_dotenv('.env.defaults', override=False)
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
WS_HOST = os.getenv('WS_HOST','127.0.0.1')
WS_PORT = int(os.getenv('WS_PORT','48231'))

@dataclass
class StreamingConfig:
    """Enhanced configuration with binary audio support."""
    
    # WebSocket settings
    ws_port: int = WS_PORT
    metrics_port: int = int(os.getenv("METRICS_PORT", 48232))
    ping_interval: float = float(os.getenv("PING_INTERVAL", 20.0))
    ping_timeout: float = float(os.getenv("PING_TIMEOUT", 10.0))
    
    # Binary Audio Support
    enable_binary_audio: bool = os.getenv("ENABLE_BINARY_AUDIO", "true").lower() == "true" and BINARY_AUDIO_AVAILABLE
    enable_http_metrics: bool = os.getenv("ENABLE_HTTP_METRICS", "false").lower() == "true"
    vad_threshold: float = float(os.getenv("VAD_THRESHOLD", "0.02"))
    vad_silence_duration: float = float(os.getenv("VAD_SILENCE_DURATION", "1.0"))
    max_concurrent_streams: int = int(os.getenv("MAX_CONCURRENT_STREAMS", "10"))
    audio_buffer_size: int = int(os.getenv("AUDIO_BUFFER_SIZE", "4096"))

config = StreamingConfig()

# Mock classes for standalone operation
class MockSTTProcessor:
    """Mock STT processor for testing"""
    def __init__(self, config=None):
        self.config = config
        logger.info("🎤 Mock STT Processor initialized")
    
    async def initialize(self):
        logger.info("✅ Mock STT initialized")
    
    async def transcribe_audio(self, audio_data: bytes) -> str:
        await asyncio.sleep(0.1)  # Simulate processing
        return f"Mock transcription of {len(audio_data)} bytes of audio"

class MockTTSManager:
    """Mock TTS manager for testing"""
    def __init__(self):
        logger.info("🎧 Mock TTS Manager initialized")
    
    async def initialize(self, *args, **kwargs):
        logger.info("✅ Mock TTS initialized")
        return True
    
    async def synthesize(self, text: str, **kwargs):
        await asyncio.sleep(0.2)  # Simulate processing
        # Return mock audio data
        mock_audio = b"RIFF....WAVE...." + b"mock_audio_data" * 100
        from types import SimpleNamespace
        return SimpleNamespace(
            success=True,
            audio_data=mock_audio,
            engine_used="mock",
            voice_used="test_voice",
            error_message=None
        )
    
    async def cleanup(self):
        logger.info("🧹 Mock TTS cleanup")
    
    def get_available_engines(self):
        return ["mock"]
    
    def get_current_engine(self):
        return SimpleNamespace(value="mock")
    
    def get_engine_stats(self):
        return {"mock": {"calls": 0, "success": 0}}

class MinimalVoiceServer:
    """Minimal voice server for binary audio testing"""
    
    def __init__(self):
        self.stt_processor = MockSTTProcessor(config)
        self.tts_manager = MockTTSManager()
        self.connections = {}
        self.stats = {
            'connections': 0,
            'messages_processed': 0,
            'start_time': time.time()
        }
        
        logger.info("🚀 Minimal Voice Server initialized")
    
    async def initialize(self):
        """Initialize server components"""
        logger.info("🔧 Initializing server components...")
        await self.stt_processor.initialize()
        await self.tts_manager.initialize()
        logger.info("✅ Server initialization completed")
    
    async def handle_websocket(self, websocket, path=None):
        """Handle WebSocket connections"""
        client_id = str(uuid.uuid4())[:8]
        self.connections[client_id] = {
            'websocket': websocket,
            'connected_at': time.time()
        }
        self.stats['connections'] += 1
        
        logger.info(f"🔗 Client {client_id} connected")
        
        try:
            # Send server info
            await websocket.send(json.dumps({
                'type': 'server_info',
                'server_version': '2.0',
                'binary_audio_enabled': config.enable_binary_audio,
                'features': {
                    'binary_audio': config.enable_binary_audio,
                    'performance_metrics': config.enable_http_metrics
                },
                'timestamp': time.time()
            }))
            
            # Message loop
            async for message in websocket:
                try:
                    self.stats['messages_processed'] += 1
                    
                    # Check if binary message
                    if isinstance(message, bytes) and config.enable_binary_audio:
                        await self._handle_binary_message(websocket, message, client_id)
                    else:
                        # Handle JSON message
                        data = json.loads(message)
                        await self._handle_json_message(websocket, data, client_id)
                        
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': 'Invalid JSON format'
                    }))
                except Exception as e:
                    logger.error(f"Message processing error: {e}")
                    break
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"📱 Client {client_id} disconnected")
        except Exception as e:
            logger.error(f"WebSocket error for {client_id}: {e}")
        finally:
            if client_id in self.connections:
                del self.connections[client_id]
    
    async def _handle_binary_message(self, websocket, data: bytes, client_id: str):
        """Handle binary audio message"""
        try:
            # Try to parse binary frame
            if not hasattr(self, '_binary_handler'):
                self._binary_handler = BinaryAudioHandler()
            
            frame = self._binary_handler.parse_binary_frame(data)
            if frame:
                # Simulate processing
                transcription = await self.stt_processor.transcribe_audio(frame.audio_data)
                tts_result = await self.tts_manager.synthesize(f"You said: {transcription}")
                
                # Send response
                audio_b64 = base64.b64encode(tts_result.audio_data).decode('utf-8')
                await websocket.send(json.dumps({
                    'type': 'response',
                    'transcription': transcription,
                    'content': f"Binary audio processed: {transcription}",
                    'audio': f"data:audio/wav;base64,{audio_b64}",
                    'stream_id': frame.stream_id,
                    'binary_processed': True,
                    'timestamp': time.time()
                }))
                
                logger.info(f"📡 Processed binary frame from {client_id}: {len(frame.audio_data)} bytes")
            else:
                await websocket.send(json.dumps({
                    'type': 'error',
                    'message': 'Invalid binary frame format'
                }))
                
        except Exception as e:
            logger.error(f"Binary message error: {e}")
            await websocket.send(json.dumps({
                'type': 'error',
                'message': f'Binary processing failed: {str(e)}'
            }))
    
    async def _handle_json_message(self, websocket, data: Dict, client_id: str):
        """Handle JSON message"""
        message_type = data.get('type', 'unknown')
        
        if message_type == 'ping':
            await websocket.send(json.dumps({
                'type': 'pong',
                'timestamp': time.time(),
                'binary_audio_enabled': config.enable_binary_audio
            }))
        
        elif message_type == 'text':
            text = data.get('content', '')
            if text:
                # Simulate processing
                response_text = f"You said: {text}"
                tts_result = await self.tts_manager.synthesize(response_text)
                
                audio_b64 = base64.b64encode(tts_result.audio_data).decode('utf-8')
                await websocket.send(json.dumps({
                    'type': 'response',
                    'content': response_text,
                    'audio': f"data:audio/wav;base64,{audio_b64}",
                    'timestamp': time.time()
                }))
        
        elif message_type == 'get_status':
            await websocket.send(json.dumps({
                'type': 'status',
                'server_stats': self.get_stats(),
                'binary_audio_enabled': config.enable_binary_audio,
                'timestamp': time.time()
            }))
        
        else:
            logger.warning(f"Unknown message type from {client_id}: {message_type}")
    
    def get_stats(self):
        """Get server statistics"""
        uptime = time.time() - self.stats['start_time']
        return {
            'uptime_seconds': uptime,
            'total_connections': self.stats['connections'],
            'active_connections': len(self.connections),
            'messages_processed': self.stats['messages_processed'],
            'binary_audio_enabled': config.enable_binary_audio
        }

# Create server instance
server = MinimalVoiceServer()

async def main():
    """Main server startup"""
    try:
        # Display startup banner
        print("\n" + "=" * 60)
        print("🎤 Enhanced Voice Assistant Backend Starting...")
        if config.enable_binary_audio:
            print("🎵 Binary Audio Protocol v2.0: ENABLED")
            print("📊 Performance Metrics: ENABLED")
            print("🔄 Backwards Compatibility: ENABLED")
        else:
            print("🔄 Legacy JSON Protocol: ENABLED")
        print("=" * 60)
        
        # Initialize server
        await server.initialize()
        
        # Start WebSocket server
        logger.info(f"🔗 Starting WebSocket server on {WS_HOST}:{WS_PORT}...")
        
        # WebSocket configuration
        websocket_config = {
            'close_timeout': 10,
            'ping_interval': config.ping_interval,
            'ping_timeout': config.ping_timeout,
            'max_size': 10**7,  # 10MB for binary frames
        }
        
        if config.enable_binary_audio:
            websocket_config['compression'] = None
            logger.info("🎵 Binary frame support: Compression disabled")
        
        async with websockets.serve(
            server.handle_websocket,
            WS_HOST, WS_PORT,
            **websocket_config
        ):
            print("\n" + "=" * 60)
            print("🚀 Enhanced Voice Assistant Server is running!")
            print(f"🔗 WebSocket: ws://{WS_HOST}:{WS_PORT}")
            if config.enable_binary_audio:
                print("🎵 Binary Audio Protocol v2.0: ACTIVE")
                print("📊 Performance Monitoring: ACTIVE")
            print("🔄 Press Ctrl+C to stop")
            print("=" * 60)
            
            # Run forever
            await asyncio.Future()
            
    except Exception as e:
        logger.error(f"❌ Server startup failed: {e}")
        import traceback
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        raise
    finally:
        logger.info("🧹 Server cleanup...")
        await server.tts_manager.cleanup()

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
