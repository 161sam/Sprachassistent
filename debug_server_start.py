#!/usr/bin/env python3
"""
Debug-Script für WebSocket-Server Start-Probleme
"""

import sys
import traceback
import os
from pathlib import Path

# Gleicher PYTHONPATH bootstrap wie im Server
_PROJECT_ROOT = Path(__file__).resolve().parents[0]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

def debug_imports():
    """Teste alle kritischen Imports"""
    
    print("=== DEBUG: Import-Tests ===")
    
    try:
        print("✓ asyncio, websockets, json, base64, time, uuid")
        import asyncio, websockets, json, base64, time, uuid
    except Exception as e:
        print(f"✗ Standard Libraries: {e}")
        return False
    
    try:
        print("✓ numpy, os, logging, datetime")
        import numpy, os, logging
        from datetime import datetime
    except Exception as e:
        print(f"✗ Numpy/Standard: {e}")
        return False
        
    try:
        print("✓ typing, dataclasses, concurrent.futures, collections")
        from typing import Dict, Optional, List, AsyncGenerator
        from dataclasses import dataclass, field
        from concurrent.futures import ThreadPoolExecutor
        from collections import deque
    except Exception as e:
        print(f"✗ Typing/Collections: {e}")
        return False
        
    try:
        print("✓ aiohttp, aiofiles")
        import aiohttp, aiofiles
    except Exception as e:
        print(f"✗ AIOHTTP: {e}")
        return False
        
    try:
        print("✓ faster_whisper")
        from faster_whisper import WhisperModel
    except Exception as e:
        print(f"✗ FasterWhisper: {e}")
        return False
        
    try:
        print("✓ pathlib, dotenv")
        from pathlib import Path
        from dotenv import load_dotenv
    except Exception as e:
        print(f"✗ Path/DotEnv: {e}")
        return False
        
    # Backend modules
    try:
        print("✓ backend.tts imports")
        from backend.tts import TTSManager, TTSEngineType, TTSConfig
    except Exception as e:
        print(f"✗ Backend.TTS: {e}")
        traceback.print_exc()
        return False
        
    try:
        print("✓ auth.token_utils")
        from auth.token_utils import verify_token
    except Exception as e:
        print(f"✗ Auth: {e}")
        traceback.print_exc()
        return False
        
    try:
        print("✓ intent_classifier")
        from intent_classifier import IntentClassifier
    except Exception as e:
        print(f"✗ Intent Classifier: {e}")
        traceback.print_exc()
        return False
        
    try:
        print("✓ skills")
        from skills import load_all_skills
    except Exception as e:
        print(f"✗ Skills: {e}")
        traceback.print_exc()
        return False
        
    try:
        print("✓ metrics_api")
        from metrics_api import start_metrics_api
    except Exception as e:
        print(f"✗ Metrics API: {e}")
        traceback.print_exc()
        return False
        
    print("\n=== ✅ Alle Imports erfolgreich ===")
    return True

def debug_configs():
    """Teste Konfigurationen"""
    print("\n=== DEBUG: ENV-Konfiguration ===")
    
    # Load ENV
    try:
        from dotenv import load_dotenv
        load_dotenv('.env.defaults', override=False)
        load_dotenv()
        print("✓ ENV-Dateien geladen")
    except Exception as e:
        print(f"✗ ENV-Load Error: {e}")
        return False
        
    # Critical ENV vars
    ws_host = os.getenv('WS_HOST', '127.0.0.1')
    ws_port = int(os.getenv('WS_PORT', '48231'))
    metrics_port = int(os.getenv('METRICS_PORT', '48232'))
    
    print(f"  WS_HOST: {ws_host}")
    print(f"  WS_PORT: {ws_port}")
    print(f"  METRICS_PORT: {metrics_port}")
    
    # TTS configs
    tts_engine = os.getenv('TTS_ENGINE', 'piper')
    tts_model_dir = os.getenv('TTS_MODEL_DIR', 'models')
    
    print(f"  TTS_ENGINE: {tts_engine}")
    print(f"  TTS_MODEL_DIR: {tts_model_dir}")
    
    # Check Model Dir
    if os.path.exists(tts_model_dir):
        print(f"✓ TTS Model Directory exists: {tts_model_dir}")
    else:
        print(f"✗ TTS Model Directory missing: {tts_model_dir}")
        
    return True

def debug_server_init():
    """Teste Server-Initialisierung Schritt für Schritt"""
    print("\n=== DEBUG: Server-Initialisierung ===")
    
    try:
        # Change to backend/ws-server directory for proper imports
        os.chdir('/home/saschi/Sprachassistent/backend/ws-server')
        
        # Try importing the server class
        from ws_server import OptimizedVoiceServer
        print("✓ OptimizedVoiceServer import erfolgreich")
        
        # Try creating instance
        server = OptimizedVoiceServer()
        print("✓ Server-Instanz erstellt")
        
        return server
        
    except Exception as e:
        print(f"✗ Server-Init Error: {e}")
        traceback.print_exc()
        return None

async def debug_async_init(server):
    """Teste asynchrone Initialisierung"""
    print("\n=== DEBUG: Async Initialisierung ===")
    
    try:
        print("Starte server.initialize()...")
        await server.initialize()
        print("✓ Server.initialize() erfolgreich")
        return True
        
    except Exception as e:
        print(f"✗ Async-Init Error: {e}")
        traceback.print_exc()
        return False

async def main():
    """Haupt-Debug-Routine"""
    print("🔍 Voice Assistant Server Debug Routine")
    print("=" * 50)
    
    # 1. Import Tests
    if not debug_imports():
        print("❌ Import-Fehler - Abbruch")
        return
        
    # 2. Config Tests  
    if not debug_configs():
        print("❌ Config-Fehler - Abbruch")
        return
        
    # 3. Server Init
    server = debug_server_init()
    if not server:
        print("❌ Server-Init-Fehler - Abbruch")
        return
        
    # 4. Async Init
    if not await debug_async_init(server):
        print("❌ Async-Init-Fehler - Abbruch")
        return
        
    print("\n🎉 ALLE DEBUG-TESTS ERFOLGREICH!")
    print("Server kann grundsätzlich initialisiert werden.")
    print("Problem liegt vermutlich beim tatsächlichen Start.")
    
    # Cleanup
    try:
        await server.tts_manager.cleanup()
    except:
        pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Debug abgebrochen")
    except Exception as e:
        print(f"\n💥 Unerwarteter Fehler: {e}")
        traceback.print_exc()
