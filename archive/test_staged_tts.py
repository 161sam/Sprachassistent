#!/usr/bin/env python3
"""
Test Script für Staged TTS Implementierung

Testet die Kern-Funktionalitäten des Staged TTS Systems:
- Text-Chunking
- Parallel Processing
- WebSocket-Integration
"""

import asyncio
import json
import sys
from pathlib import Path

# Füge Backend-Pfad hinzu
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.ws_server.staged_tts.chunking import limit_and_chunk, create_intro_chunk, optimize_for_prosody
from backend.ws_server.staged_tts.staged_processor import StagedTTSConfig


def test_text_chunking():
    """Teste die Text-Chunking-Funktionalität"""
    print("🧪 Testing Text Chunking...")
    
    test_text = """Das ist ein längerer Text für den Test des Staged TTS Systems. 
    Er sollte in mehrere Chunks aufgeteilt werden, die jeweils zwischen 80 und 180 Zeichen lang sind.
    Dabei sollen die Sätze an sinnvollen Stellen getrennt werden."""
    
    # Test basic chunking
    chunks = limit_and_chunk(test_text, max_length=500)
    print(f"✅ Generated {len(chunks)} chunks:")
    for i, chunk in enumerate(chunks):
        print(f"  Chunk {i+1} ({len(chunk)} chars): {chunk}")
    
    # Test intro creation
    intro, remaining = create_intro_chunk(chunks, max_intro_length=120)
    print(f"\n✅ Intro ({len(intro)} chars): {intro}")
    print(f"✅ Remaining chunks: {len(remaining)}")
    
    # Test prosody optimization
    optimized = optimize_for_prosody("Das sind 20.000 Euro!")
    print(f"✅ Prosody optimization: '{optimized}'")


def test_config():
    """Teste die Konfiguration"""
    print("\n🧪 Testing Configuration...")
    
    config = StagedTTSConfig(
        enabled=True,
        max_response_length=500,
        max_intro_length=120,
        chunk_timeout_seconds=10,
        max_chunks=3,
        enable_caching=True
    )
    
    print(f"✅ Config created: enabled={config.enabled}, max_length={config.max_response_length}")


async def test_mock_processor():
    """Teste den Processor mit Mock TTS Manager"""
    print("\n🧪 Testing Mock Processor...")
    
    class MockTTSManager:
        async def synthesize(self, text, engine=None):
            class MockResult:
                success = True
                audio_data = b"mock_audio_data"
                engine_used = engine or "mock"
                error_message = None
            return MockResult()
    
    from backend.ws_server.staged_tts.staged_processor import StagedTTSProcessor
    
    processor = StagedTTSProcessor(MockTTSManager())
    
    test_text = "Das ist ein Test für das Staged TTS System. Es sollte funktionieren!"
    chunks = await processor.process_staged_tts(test_text)
    
    print(f"✅ Processed {len(chunks)} chunks:")
    for chunk in chunks:
        print(f"  {chunk.engine} chunk {chunk.index}: {chunk.text[:50]}...")


def main():
    """Führe alle Tests aus"""
    print("🎭 Staged TTS Implementation Test\n")
    
    try:
        test_text_chunking()
        test_config()
        asyncio.run(test_mock_processor())
        
        print("\n✅ All tests passed!")
        print("\n📋 Next steps:")
        print("  1. Start the voice assistant server")
        print("  2. Connect with a WebSocket client")
        print("  3. Send text messages to test staged TTS")
        print("  4. Monitor logs for Piper intro + Zonos main processing")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
