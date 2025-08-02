#!/usr/bin/env python3
"""
TTS Engine Module für Sprachassistent
Unterstützt Piper und Kokoro TTS mit Realtime-Switching
"""

from .base_tts_engine import (
    BaseTTSEngine, 
    TTSConfig, 
    TTSResult, 
    TTSEngineError, 
    TTSInitializationError, 
    TTSSynthesisError, 
    TTSVoiceNotSupportedError
)

from .piper_tts_engine import PiperTTSEngine
from .kokoro_tts_engine import KokoroTTSEngine
from .tts_manager import TTSManager, TTSEngineType, create_default_tts_manager, quick_synthesize

__version__ = "1.0.0"
__author__ = "Sprachassistent Team"
__all__ = [
    # Base classes
    "BaseTTSEngine",
    "TTSConfig", 
    "TTSResult",
    
    # Exceptions
    "TTSEngineError",
    "TTSInitializationError", 
    "TTSSynthesisError",
    "TTSVoiceNotSupportedError",
    
    # Engine implementations
    "PiperTTSEngine",
    "KokoroTTSEngine",
    
    # Manager
    "TTSManager",
    "TTSEngineType",
    
    # Convenience functions
    "create_default_tts_manager",
    "quick_synthesize"
]

# Modul-Level Dokumentation
__doc__ = """
TTS Engine Module für flexibles Text-to-Speech

Beispiel-Verwendung:

1. Einfache Nutzung:
```python
from backend.tts import quick_synthesize

result = await quick_synthesize("Hallo Welt", engine="piper")
if result.success:
    with open("output.wav", "wb") as f:
        f.write(result.audio_data)
```

2. Manager-basierte Nutzung:
```python
from backend.tts import TTSManager, TTSEngineType

manager = TTSManager()
await manager.initialize()

# Piper verwenden
await manager.switch_engine(TTSEngineType.PIPER)
result = await manager.synthesize("Deutscher Text", voice="de-thorsten-low")

# Zu Kokoro wechseln
await manager.switch_engine(TTSEngineType.KOKORO)
result = await manager.synthesize("English text", voice="af_sarah")

await manager.cleanup()
```

3. Eigene Engine-Konfiguration:
```python
from backend.tts import TTSManager, TTSConfig, TTSEngineType

piper_config = TTSConfig(
    engine_type="piper",
    voice="de-kerstin-low",
    speed=1.2,
    language="de"
)

kokoro_config = TTSConfig(
    engine_type="kokoro", 
    voice="af_heart",
    speed=0.9,
    language="en"
)

manager = TTSManager()
await manager.initialize(piper_config, kokoro_config)
```

Unterstützte Engines:
- Piper TTS: Hochqualitative deutsche Stimmen, offline
- Kokoro TTS: Kompakte mehrsprachige Engine (~80MB)

Features:
- Realtime Engine-Switching
- Performance-Monitoring
- Asynchrone Verarbeitung
- Umfangreiche Stimmen-Auswahl
- Flexible Konfiguration
"""
