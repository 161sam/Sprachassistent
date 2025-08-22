"""
Enhanced WebSocket Server with Binary Audio Support
Integrates with existing ws-server.py while maintaining backwards compatibility
"""

import asyncio
import websockets
import json
import logging
import time
from typing import Dict, Any, Optional
from pathlib import Path
import sys

# Import the binary handler (from the previous artifact)
from ws_server.protocol.binary_v2 import WebSocketBinaryRouter, BinaryAudioHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedWebSocketServer:
    """Enhanced WebSocket server with binary audio support"""
    
    def __init__(self, existing_stt_processor, existing_tts_processor, config):
        self.stt_processor = existing_stt_processor
        self.tts_processor = existing_tts_processor
        self.config = config
        
        # Initialize existing message handler (compatibility)
        self.legacy_message_handler = LegacyMessageHandler(
            self.stt_processor, 
            self.tts_processor, 
            self.config
        )
        
        # Initialize binary router
        self.binary_router = WebSocketBinaryRouter(
            self.legacy_message_handler, 
            self.stt_processor
        )
        
        # Connection tracking
        self.connections: Dict[str, dict] = {}
        self.server_metrics = {
            'start_time': time.time(),
            'total_connections': 0,
            'active_connections': 0,
            'messages_processed': 0,
            'binary_messages': 0,
            'json_messages': 0
        }
    
    async def register_connection(self, websocket, path):
        """Register new WebSocket connection"""
        connection_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}_{time.time()}"
        
        self.connections[connection_id] = {
            'websocket': websocket,
            'path': path,
            'connect_time': time.time(),
            'capabilities': {},
            'message_count': 0,
            'binary_supported': False
        }
        
        self.server_metrics['total_connections'] += 1
        self.server_metrics['active_connections'] = len(self.connections)
        
        logger.info(f"New connection registered: {connection_id}")
        return connection_id
    
    async def unregister_connection(self, connection_id):
        """Unregister WebSocket connection"""
        if connection_id in self.connections:
            del self.connections[connection_id]
            self.server_metrics['active_connections'] = len(self.connections)
            logger.info(f"Connection unregistered: {connection_id}")
    
    async def handle_client(self, websocket, path):
        """Main client handler with binary support"""
        connection_id = await self.register_connection(websocket, path)
        
        try:
            # Send initial greeting with capabilities
            await self.send_server_info(websocket)
            
            # Message handling loop
            async for message in websocket:
                try:
                    # Update connection metrics
                    self.connections[connection_id]['message_count'] += 1
                    self.server_metrics['messages_processed'] += 1
                    
                    # Route message through binary router
                    if isinstance(message, bytes):
                        self.server_metrics['binary_messages'] += 1
                        logger.debug(f"Processing binary message: {len(message)} bytes")
                    else:
                        self.server_metrics['json_messages'] += 1
                        logger.debug(f"Processing JSON message: {len(message)} chars")
                    
                    # Use binary router for all message handling
                    await self.binary_router.handle_message(websocket, message)
                    
                except Exception as e:
                    logger.error(f"Error processing message from {connection_id}: {e}")
                    await self.send_error(websocket, f"Message processing error: {str(e)}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {connection_id} disconnected")
        except Exception as e:
            logger.error(f"Error handling client {connection_id}: {e}")
        finally:
            await self.unregister_connection(connection_id)
    
    async def send_server_info(self, websocket):
        """Send server information and capabilities"""
        server_info = {
            'type': 'server_info',
            'timestamp': time.time(),
            'server_version': '2.0',
            'features': {
                'binary_audio': True,
                'vad_support': True,
                'streaming_stt': True,
                'staged_tts': True,
                'performance_metrics': True
            },
            'supported_formats': {
                'audio': ['pcm', 'wav'],
                'sample_rates': [16000, 44100, 48000],
                'channels': [1, 2]
            },
            'protocols': {
                'websocket': '13',
                'audio_protocol': '2.0'
            }
        }
        
        try:
            await websocket.send(json.dumps(server_info))
        except Exception as e:
            logger.error(f"Error sending server info: {e}")
    
    async def send_error(self, websocket, error_message):
        """Send error message to client"""
        error_response = {
            'type': 'error',
            'timestamp': time.time(),
            'message': error_message
        }
        
        try:
            await websocket.send(json.dumps(error_response))
        except Exception as e:
            logger.error(f"Error sending error response: {e}")
    
    def get_server_metrics(self):
        """Get comprehensive server metrics"""
        current_time = time.time()
        uptime = current_time - self.server_metrics['start_time']
        
        return {
            'server': {
                **self.server_metrics,
                'uptime_seconds': uptime,
                'messages_per_second': self.server_metrics['messages_processed'] / max(uptime, 1)
            },
            'binary_handler': self.binary_router.get_metrics(),
            'connections': {
                conn_id: {
                    'connected_duration': current_time - conn_info['connect_time'],
                    'message_count': conn_info['message_count'],
                    'binary_supported': conn_info['binary_supported']
                }
                for conn_id, conn_info in self.connections.items()
            }
        }

class LegacyMessageHandler:
    """Wrapper for existing message handling logic"""
    
    def __init__(self, stt_processor, tts_processor, config):
        self.stt_processor = stt_processor
        self.tts_processor = tts_processor
        self.config = config
    
    async def handle_message(self, websocket, data):
        """Handle legacy JSON messages - maintains backwards compatibility"""
        try:
            message_type = data.get('type')
            
            if message_type == 'audio_data':
                await self.handle_audio_message(websocket, data)
            elif message_type == 'text_input':
                await self.handle_text_message(websocket, data)
            elif message_type == 'get_metrics':
                await self.handle_metrics_request(websocket, data)
            elif message_type == 'settings_update':
                await self.handle_settings_update(websocket, data)
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except Exception as e:
            logger.error(f"Error in legacy message handler: {e}")
            raise
    
    async def handle_audio_message(self, websocket, data):
        """Handle audio message (base64 format for legacy compatibility)"""
        try:
            # Extract audio data
            if data.get('format') == 'base64':
                import base64
                audio_data = base64.b64decode(data['audio_data'])
            else:
                # If already bytes (from binary handler conversion)
                audio_data = data['audio_data']
            
            # Process with STT
            if hasattr(self.stt_processor, 'process_audio_chunk'):
                result = await self.stt_processor.process_audio_chunk(
                    audio_data,
                    stream_id=data.get('stream_id'),
                    vad_info=data.get('vad_info', {})
                )
            else:
                # Fallback to existing method
                result = await self.stt_processor.process_audio(audio_data)
            
            # Send result back
            if result:
                response = {
                    'type': 'transcription_result',
                    'stream_id': data.get('stream_id'),
                    'timestamp': time.time(),
                    'text': result.get('text', ''),
                    'confidence': result.get('confidence', 0.0),
                    'is_final': result.get('is_final', True)
                }
                await websocket.send(json.dumps(response))
                
        except Exception as e:
            logger.error(f"Error processing audio message: {e}")
            raise
    
    async def handle_text_message(self, websocket, data):
        """Handle text input message"""
        try:
            text = data.get('text', '')
            if not text:
                return
            
            # Process with existing TTS pipeline (staged TTS integration)
            if hasattr(self.tts_processor, 'process_staged_tts'):
                tts_result = await self.tts_processor.process_staged_tts(text)
            else:
                tts_result = await self.tts_processor.process_text(text)
            
            # Send TTS result
            if tts_result:
                response = {
                    'type': 'tts_result',
                    'timestamp': time.time(),
                    'audio_data': tts_result.get('audio_data'),
                    'format': tts_result.get('format', 'base64'),
                    'sample_rate': tts_result.get('sample_rate', 22050)
                }
                await websocket.send(json.dumps(response))
                
        except Exception as e:
            logger.error(f"Error processing text message: {e}")
            raise
    
    async def handle_metrics_request(self, websocket, data):
        """Handle metrics request"""
        try:
            # This would be called by the main server to get metrics
            metrics = {
                'type': 'metrics_response',
                'timestamp': time.time(),
                'request_id': data.get('request_id'),
                'metrics': {}  # Would be populated by main server
            }
            await websocket.send(json.dumps(metrics))
            
        except Exception as e:
            logger.error(f"Error handling metrics request: {e}")
    
    async def handle_settings_update(self, websocket, data):
        """Handle settings update"""
        try:
            settings = data.get('settings', {})
            # Update configuration
            for key, value in settings.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
            
            response = {
                'type': 'settings_updated',
                'timestamp': time.time(),
                'updated_settings': settings
            }
            await websocket.send(json.dumps(response))
            
        except Exception as e:
            logger.error(f"Error updating settings: {e}")

# Integration example for existing ws-server.py
async def create_enhanced_server(host='localhost', port=8765, config=None):
    """Create enhanced server with binary support"""
    
    # Initialize existing processors (these would be your actual processors)
    from your_existing_modules import STTProcessor, TTSProcessor, Config
    
    stt_processor = STTProcessor(config)
    tts_processor = TTSProcessor(config)
    
    # Create enhanced server
    enhanced_server = EnhancedWebSocketServer(
        stt_processor, 
        tts_processor, 
        config or Config()
    )
    
    # Start server
    async with websockets.serve(enhanced_server.handle_client, host, port):
        logger.info(f"Enhanced WebSocket server started on {host}:{port}")
        logger.info("Supported features: Binary audio, VAD, Streaming STT, Staged TTS")
        
        # Keep server running
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    # Example usage
    asyncio.run(create_enhanced_server())
