import struct
import json
import logging
from typing import Dict, Any, Optional
import time
from dataclasses import dataclass

from ws_server.metrics.collector import collector

logger = logging.getLogger(__name__)


@dataclass
class BinaryFrame:
    """Represents a parsed binary audio frame"""
    stream_id: str
    sequence: int
    timestamp: float
    audio_data: bytes
    frame_size: int


def build_audio_frame(stream_id: str, sequence: int, timestamp: float, audio_data: bytes) -> bytes:
    """Build a binary audio frame.

    The frame layout is:
    [stream_id_length:1][stream_id][sequence:4][timestamp:8][audio]
    where integers are big-endian.
    """
    sid_bytes = stream_id.encode("utf-8")
    if len(sid_bytes) > 255:
        raise ValueError("stream_id too long")

    header = struct.pack(">B", len(sid_bytes)) + sid_bytes
    header += struct.pack(">I", sequence)
    header += struct.pack(">d", timestamp)
    return header + audio_data


def parse_audio_frame(data: bytes) -> BinaryFrame:
    """Parse a binary audio frame.

    Raises:
        ValueError: if the buffer is too short or malformed.
    """
    if len(data) < 1 + 4 + 8:
        raise ValueError("binary frame too short")

    stream_id_length = data[0]
    header_length = 1 + stream_id_length + 4 + 8
    if len(data) < header_length:
        raise ValueError("binary frame incomplete")

    stream_id = data[1:1 + stream_id_length].decode("utf-8")
    offset = 1 + stream_id_length
    sequence = struct.unpack(">I", data[offset:offset + 4])[0]
    offset += 4
    timestamp = struct.unpack(">d", data[offset:offset + 8])[0]
    offset += 8
    audio_data = data[offset:]

    return BinaryFrame(
        stream_id=stream_id,
        sequence=sequence,
        timestamp=timestamp,
        audio_data=audio_data,
        frame_size=len(data),
    )


class BinaryAudioHandler:
    """Handles binary audio frame processing for WebSocket server"""
    
    def __init__(self):
        self.active_streams: Dict[str, Dict] = {}
        self.metrics = {
            'frames_processed': 0,
            'bytes_received': 0,
            'parse_errors': 0,
            'active_streams': 0
        }
    
    def parse_binary_frame(self, data: bytes) -> Optional[BinaryFrame]:
        """Parse binary frame data into a :class:`BinaryFrame`.

        Any parsing error is logged and results in ``None``.
        """
        try:
            return parse_audio_frame(data)
        except ValueError as exc:
            logger.warning(f"Binary frame parsing failed: {exc}")
            self.metrics['parse_errors'] += 1
            return None

    async def handle_binary_message(self, websocket, data: bytes, stt_processor, message_handler):
        """
        Handle incoming binary audio message
        
        Args:
            websocket: WebSocket connection
            data: Binary audio frame data
            stt_processor: STT processor instance
            message_handler: Existing message handler for compatibility
        """
        try:
            # Parse binary frame
            frame = self.parse_binary_frame(data)
            if not frame:
                await self._send_error(websocket, "Invalid binary frame format")
                return

            # Determine expected PCM parameters from STT processor or defaults
            expected_sr = getattr(stt_processor, "sample_rate", 16000)
            expected_ch = getattr(stt_processor, "channels", 1)

            # Validate PCM frame size (16-bit samples)
            if len(frame.audio_data) % (2 * expected_ch) != 0:
                await self._send_error(websocket, "Ungültige PCM-Framelänge")
                return

            # Update metrics
            self.metrics['frames_processed'] += 1
            self.metrics['bytes_received'] += frame.frame_size
            collector.audio_in_bytes_total.inc(len(frame.audio_data))
            
            # Track stream
            if frame.stream_id not in self.active_streams:
                self.active_streams[frame.stream_id] = {
                    'start_time': time.time(),
                    'last_sequence': -1,
                    'frame_count': 0,
                    'total_audio_bytes': 0,
                    'sample_rate': expected_sr,
                    'channels': expected_ch,
                }
                self.metrics['active_streams'] = len(self.active_streams)

            stream_info = self.active_streams[frame.stream_id]

            # Ensure PCM parameters stay consistent per stream
            if (
                stream_info['sample_rate'] != expected_sr
                or stream_info['channels'] != expected_ch
            ):
                await self._send_error(websocket, "PCM-Parameter unterscheiden sich vom Stream-Setup")
                return
            
            # Check sequence order (optional - for debugging)
            if frame.sequence <= stream_info['last_sequence']:
                logger.warning(f"Out of order frame: {frame.sequence} <= {stream_info['last_sequence']}")
            
            stream_info['last_sequence'] = frame.sequence
            stream_info['frame_count'] += 1
            stream_info['total_audio_bytes'] += len(frame.audio_data)
            
            # Convert to format compatible with existing STT pipeline
            audio_message = {
                'type': 'audio_data',
                'stream_id': frame.stream_id,
                'sequence': frame.sequence,
                'timestamp': frame.timestamp,
                'audio_data': frame.audio_data,  # Keep as bytes for efficiency
                'format': 'binary',
                'sample_rate': expected_sr,
                'channels': expected_ch,
            }
            
            # Process through existing STT pipeline
            await self._process_audio_data(websocket, audio_message, stt_processor, message_handler)
            
        except Exception as e:
            logger.error(f"Error handling binary message: {e}")
            await self._send_error(websocket, f"Binary processing error: {str(e)}")
    
    async def _process_audio_data(self, websocket, audio_message, stt_processor, message_handler):
        """Process audio data through existing STT pipeline"""
        try:
            # Check if STT processor expects bytes or base64
            if hasattr(stt_processor, 'process_binary_audio'):
                # Direct binary processing if supported
                result = await stt_processor.process_binary_audio(
                    audio_message['audio_data'],
                    stream_id=audio_message['stream_id'],
                    sequence=audio_message['sequence']
                )
            else:
                # Convert to base64 for compatibility with existing pipeline
                import base64
                audio_message['audio_data'] = base64.b64encode(audio_message['audio_data']).decode('utf-8')
                audio_message['format'] = 'base64'
                
                # Use existing message handler
                result = await message_handler.handle_audio_message(websocket, audio_message)
            
            # Send response if we have results
            if result:
                await self._send_response(websocket, result, audio_message['stream_id'])
                
        except Exception as e:
            logger.error(f"Error processing audio data: {e}")
            await self._send_error(websocket, f"STT processing error: {str(e)}")
    
    async def _send_response(self, websocket, result, stream_id):
        """Send response back to client"""
        response = {
            'type': 'stt_result',
            'stream_id': stream_id,
            'timestamp': time.time(),
            'result': result
        }
        
        try:
            await websocket.send(json.dumps(response))
        except Exception as e:
            logger.error(f"Error sending response: {e}")
    
    async def _send_error(self, websocket, error_message):
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
    
    def cleanup_stream(self, stream_id: str):
        """Clean up completed stream"""
        if stream_id in self.active_streams:
            del self.active_streams[stream_id]
            self.metrics['active_streams'] = len(self.active_streams)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current processing metrics"""
        return {
            **self.metrics,
            'streams_info': {
                stream_id: {
                    'duration': time.time() - info['start_time'],
                    'frame_count': info['frame_count'],
                    'total_audio_bytes': info['total_audio_bytes'],
                    'avg_frame_size': info['total_audio_bytes'] / max(info['frame_count'], 1)
                }
                for stream_id, info in self.active_streams.items()
            }
        }

class WebSocketBinaryRouter:
    """Routes WebSocket messages to appropriate handlers"""
    
    def __init__(self, existing_message_handler, stt_processor):
        self.binary_handler = BinaryAudioHandler()
        self.message_handler = existing_message_handler
        self.stt_processor = stt_processor
        self.client_capabilities: Dict[str, Dict] = {}
    
    async def handle_message(self, websocket, message):
        """Route message to appropriate handler based on type"""
        try:
            # Check if it's binary data
            if isinstance(message, bytes):
                await self.binary_handler.handle_binary_message(
                    websocket, message, self.stt_processor, self.message_handler
                )
            else:
                # Handle text/JSON messages
                try:
                    data = json.loads(message)
                    
                    # Handle capability negotiation
                    if data.get('type') == 'capability_negotiation':
                        await self._handle_capability_negotiation(websocket, data)
                    else:
                        # Route to existing message handler
                        await self.message_handler.handle_message(websocket, data)
                        
                except json.JSONDecodeError:
                    logger.error("Invalid JSON message received")
                    await self._send_error(websocket, "Invalid JSON format")
                    
        except Exception as e:
            logger.error(f"Error routing message: {e}")
            await self._send_error(websocket, f"Message routing error: {str(e)}")
    
    async def _handle_capability_negotiation(self, websocket, data):
        """Handle client capability negotiation"""
        client_id = data.get('client_id', 'unknown')
        client_capabilities = data.get('capabilities', {})
        
        # Store client capabilities
        self.client_capabilities[client_id] = client_capabilities
        
        # Send server capabilities
        server_capabilities = {
            'type': 'server_capabilities',
            'capabilities': {
                'binary_audio': True,
                'vad_support': True,
                'streaming_stt': True,
                'performance_metrics': True,
                'audio_formats': ['pcm', 'wav'],
                'sample_rates': [16000, 44100, 48000],
                'protocol_version': '2.0'
            },
            'timestamp': time.time()
        }
        
        await websocket.send(json.dumps(server_capabilities))
        logger.info(f"Capability negotiation completed for client {client_id}")
    
    async def _send_error(self, websocket, error_message):
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
    
    def get_metrics(self):
        """Get comprehensive metrics"""
        return {
            'binary_handler': self.binary_handler.get_metrics(),
            'connected_clients': len(self.client_capabilities),
            'client_capabilities': self.client_capabilities
        }
