"""
Compatibility layer for smooth integration with existing codebase
"""

import asyncio
import base64
import json
import time
from typing import Dict, Any, Optional, Union

class CompatibilityWrapper:
    """Wraps existing processors to work with new binary system"""
    
    @staticmethod
    def adapt_stt_processor(existing_processor):
        """Adapt existing STT processor for binary audio"""
        
        # Add binary processing method if not present
        if not hasattr(existing_processor, 'process_binary_audio'):
            async def process_binary_audio(audio_data: bytes, stream_id: str = "", 
                                         sequence: int = 0, **kwargs):
                # Convert binary to format expected by existing processor
                if hasattr(existing_processor, 'process_audio_chunk'):
                    return await existing_processor.process_audio_chunk(audio_data, **kwargs)
                elif hasattr(existing_processor, 'process_audio'):
                    return await existing_processor.process_audio(audio_data)
                else:
                    # Fallback: assume sync processing
                    return existing_processor.transcribe(audio_data)
            
            existing_processor.process_binary_audio = process_binary_audio
        
        return existing_processor
    
    @staticmethod
    def adapt_tts_processor(existing_processor):
        """Adapt existing TTS processor for enhanced features"""
        
        # Add staged TTS support if not present
        if not hasattr(existing_processor, 'process_staged_tts'):
            async def process_staged_tts(text: str, **kwargs):
                # Use existing TTS method
                if hasattr(existing_processor, 'synthesize_async'):
                    return await existing_processor.synthesize_async(text, **kwargs)
                elif hasattr(existing_processor, 'synthesize'):
                    return existing_processor.synthesize(text, **kwargs)
                else:
                    # Fallback
                    return {'audio_data': b'', 'format': 'wav', 'sample_rate': 22050}
            
            existing_processor.process_staged_tts = process_staged_tts
        
        return existing_processor

# Mock classes for development/testing
class MockSTTProcessor:
    def __init__(self, config):
        self.config = config
    
    async def process_binary_audio(self, audio_data: bytes, **kwargs):
        await asyncio.sleep(0.1)  # Simulate processing
        return {
            'text': f"Mock transcription of {len(audio_data)} bytes",
            'confidence': 0.95,
            'is_final': True
        }
    
    async def process_audio_chunk(self, audio_data: bytes, **kwargs):
        return await self.process_binary_audio(audio_data, **kwargs)

class MockTTSProcessor:
    def __init__(self, config):
        self.config = config
        self.staged_tts_enabled = True
    
    async def process_staged_tts(self, text: str, **kwargs):
        await asyncio.sleep(0.2)  # Simulate processing
        return {
            'audio_data': base64.b64encode(b'mock audio data').decode(),
            'format': 'wav',
            'sample_rate': 22050
        }

class MockConfig:
    def __init__(self):
        self.stt_model = 'mock'
        self.tts_model = 'mock'
        self.host = 'localhost'
        self.port = 8765
        self.enable_binary_audio = True
        self.enable_http_metrics = False
        self.log_level = 'INFO'
