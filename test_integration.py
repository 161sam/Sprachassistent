#!/usr/bin/env python3
"""
Staged TTS Integration Test

Führt einen umfassenden Test des implementierten Systems durch.
"""

import os
import sys
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend" / "ws-server"))

def test_imports():
    """Test all imports"""
    print("🔍 Testing imports...")
    
    try:
        from staged_tts.chunking import limit_and_chunk, create_intro_chunk, optimize_for_prosody
        print("  ✅ Chunking module imported successfully")
        
        from staged_tts.staged_processor import StagedTTSProcessor, StagedTTSConfig, TTSChunk
        print("  ✅ Staged processor module imported successfully")
        
        return True
    except ImportError as e:
        print(f"  ❌ Import error: {e}")
        return False

def test_chunking():
    """Test text chunking functionality"""
    print("\n🧩 Testing text chunking...")
    
    from staged_tts.chunking import limit_and_chunk, create_intro_chunk, optimize_for_prosody
    
    # Test text
    test_text = """Das ist ein längerer Test-Text für das Staged TTS System. 
    Er demonstriert die Funktionalität der Textaufteilung in sinnvolle Chunks.
    Jeder Chunk sollte zwischen 80 und 180 Zeichen lang sein."""
    
    # Test chunking
    chunks = limit_and_chunk(test_text, 500)
    print(f"  ✅ Generated {len(chunks)} chunks")
    
    # Test intro creation  
    intro, remaining = create_intro_chunk(chunks, 120)
    print(f"  ✅ Intro: {len(intro)} chars, Remaining: {len(remaining)} chunks")
    
    # Test prosody optimization
    optimized = optimize_for_prosody("Das sind 20.000 Euro!")
    print(f"  ✅ Prosody optimization: '{optimized}'")
    
    return True

def test_configuration():
    """Test configuration system"""
    print("\n⚙️  Testing configuration...")
    
    from staged_tts.staged_processor import StagedTTSConfig
    
    config = StagedTTSConfig(
        enabled=True,
        max_response_length=500,
        max_intro_length=120,
        chunk_timeout_seconds=10,
        max_chunks=3,
        enable_caching=True
    )
    
    print(f"  ✅ Config created: enabled={config.enabled}")
    print(f"  ✅ Max response length: {config.max_response_length}")
    print(f"  ✅ Max intro length: {config.max_intro_length}")
    
    return True

def test_file_structure():
    """Test file structure"""
    print("\n📁 Testing file structure...")
    
    required_files = [
        "backend/ws-server/staged_tts/__init__.py",
        "backend/ws-server/staged_tts/chunking.py", 
        "backend/ws-server/staged_tts/staged_processor.py",
        "docs/STAGED_TTS.md",
        ".env.staged-tts.example"
    ]
    
    all_exist = True
    for file_path in required_files:
        full_path = project_root / file_path
        if full_path.exists():
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ Missing: {file_path}")
            all_exist = False
    
    return all_exist

def test_websocket_integration():
    """Test WebSocket integration readiness"""
    print("\n🔗 Testing WebSocket integration...")
    
    # Check if ws-server.py has been modified correctly
    ws_server_path = project_root / "backend" / "ws-server" / "ws-server.py"
    
    if not ws_server_path.exists():
        print("  ❌ ws-server.py not found")
        return False
    
    content = ws_server_path.read_text()
    
    required_parts = [
        "from staged_tts import StagedTTSProcessor",
        "StagedTTSConfig",
        "staged_tts_enabled",
        "_handle_staged_tts_response",
        "_handle_staged_tts_control",
        "tts_chunk",
        "tts_sequence_end"
    ]
    
    all_found = True
    for part in required_parts:
        if part in content:
            print(f"  ✅ Found: {part}")
        else:
            print(f"  ❌ Missing: {part}")
            all_found = False
    
    return all_found

def main():
    """Run all tests"""
    print("🎭 Staged TTS Implementation - Integration Test")
    print("=" * 50)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Imports", test_imports),
        ("Text Chunking", test_chunking),
        ("Configuration", test_configuration),
        ("WebSocket Integration", test_websocket_integration)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"  ❌ Test failed with exception: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} {test_name}")
        all_passed = all_passed and passed
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All tests passed! Staged TTS is ready to use.")
        print("\n📋 Next steps:")
        print("  1. Start the voice assistant server")
        print("  2. Enable staged TTS in your .env file")
        print("  3. Test with WebSocket client")
        print("  4. Monitor logs for staged processing")
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
