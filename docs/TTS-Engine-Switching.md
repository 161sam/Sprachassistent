# TTS Engine Switching System

## Übersicht

Das Sprachassistent-System unterstützt jetzt flexibles Text-to-Speech (TTS) mit Echtzeitwechsel zwischen verschiedenen TTS-Engines:

- **Piper TTS**: Hochqualitative deutsche Stimmen, optimiert für deutsche Sprache
- **Kokoro TTS**: Kompakte mehrsprachige Engine (~80MB), schnelle Inferenz

## Features

### 🔄 Realtime Engine-Switching
- Nahtloser Wechsel zwischen TTS-Engines während der Laufzeit
- Keine Unterbrechung des Sprachassistenten
- Engine-spezifische Stimmen und Konfigurationen

### 🎵 Umfangreiche Stimmen-Auswahl
- **Piper**: Deutsche Stimmen (thorsten, kerstin, eva_k, ramona, karlsson)
- **Kokoro**: Internationale Stimmen (af_sarah, af_heart, af_sky, af_nova, etc.)

### 📊 Performance-Monitoring
- Latenz-Tracking für jede Engine
- Erfolgsraten und Fehlerstatistiken
- Automatische Qualitätsmessung

### 🎛️ GUI-Integration
- Intuitive Benutzeroberfläche zum Engine-Wechsel
- Live-Anzeige der aktuellen Engine
- Stimmen-Auswahl und Test-Funktionen

## Installation

### 1. Piper TTS (bereits vorhanden)
```bash
# Piper sollte bereits installiert sein
piper --version
```

### 2. Kokoro TTS installieren
```bash
# Automatische Installation
cd /home/saschi/Sprachassistent
chmod +x scripts/install-kokoro.sh
./scripts/install-kokoro.sh
```

### 3. System testen
```bash
# TTS-System testen
cd backend
python3 test_tts_system.py
```

## Verwendung

### WebSocket API

#### Engine wechseln
```javascript
{
  "type": "switch_tts_engine",
  "engine": "kokoro"  // oder "piper"
}
```

#### Stimme setzen
```javascript
{
  "type": "set_tts_voice",
  "voice": "af_sarah",
  "engine": "kokoro"  // optional
}
```

#### TTS-Informationen abrufen
```javascript
{
  "type": "get_tts_info"
}
```

#### Text mit spezifischer Engine
```javascript
{
  "type": "text",
  "content": "Hallo Welt",
  "tts_engine": "piper",  // optional
  "tts_voice": "de-thorsten-low"  // optional
}
```

#### Alle Engines testen
```javascript
{
  "type": "test_tts_engines",
  "text": "Test-Text"  // optional
}
```

### Python API

#### Einfache Verwendung
```python
from backend.tts import quick_synthesize

# Piper verwenden
result = await quick_synthesize(
    "Deutscher Text", 
    engine="piper", 
    voice="de-thorsten-low"
)

# Kokoro verwenden
result = await quick_synthesize(
    "English text", 
    engine="kokoro", 
    voice="af_sarah"
)
```

#### Manager-basierte Verwendung
```python
from backend.tts import TTSManager, TTSEngineType, TTSConfig

# Manager initialisieren
manager = TTSManager()
await manager.initialize()

# Engine wechseln
await manager.switch_engine(TTSEngineType.KOKORO)
result = await manager.synthesize("Hello world")

# Zu Piper wechseln
await manager.switch_engine(TTSEngineType.PIPER)
result = await manager.synthesize("Hallo Welt")

# Cleanup
await manager.cleanup()
```

### GUI-Verwendung

Das TTS Control Panel erscheint automatisch in der GUI und bietet:

1. **Engine-Auswahl**: Dropdown-Menü für verfügbare Engines
2. **Stimmen-Auswahl**: Stimmen der aktuell gewählten Engine
3. **Test-Buttons**: Einzelne Engine oder alle Engines testen
4. **Live-Status**: Aktuelle Engine und Verbindungsstatus
5. **Statistiken**: Performance-Metriken für jede Engine

## Konfiguration

Die Datei `.env` hat Vorrang vor `config/tts.json` für aktive Engine,
Voice und Timeout-Werte. `config/tts.json` definiert die Voice-Mapping- und
Wiedergabe-Defaults.

### TTS-Engines konfigurieren

#### Piper TTS
```python
piper_config = TTSConfig(
    engine_type="piper",
    model_path="/path/to/model.onnx",  # optional, auto-detection
    voice="de-thorsten-low",
    speed=1.0,
    language="de",
    sample_rate=22050,
    engine_params={
        "noise_scale": 0.667,
        "length_scale": 1.0
    }
)
```

#### Kokoro TTS
```python
kokoro_config = TTSConfig(
    engine_type="kokoro",
    model_path="/path/to/kokoro-v1.0.int8.onnx",  # optional
    voice="af_sarah",
    speed=1.0,
    language="en",
    sample_rate=24000
)
```

### Server-Konfiguration

In `archive/legacy_ws_server/ws-server-with-tts-switching.py`:

```python
config = StreamingConfig(
    default_tts_engine="piper",  # Oder "kokoro"
    enable_engine_switching=True  # Engine-Switching aktivieren
)
```

## Verfügbare Stimmen

### Piper TTS (Deutsch)
- `de-thorsten-low`: Männliche Stimme, kompakt
- `de-thorsten-medium`: Männliche Stimme, mittlere Qualität  
- `de-thorsten-high`: Männliche Stimme, hohe Qualität
- `de-kerstin-low`: Weibliche Stimme, kompakt
- `de-eva_k-low`: Weibliche Stimme, alternative
- `de-ramona-low`: Weibliche Stimme, alternative
- `de-karlsson-low`: Männliche Stimme, alternative

### Kokoro TTS (Mehrsprachig)
- `af_sarah`: Weiblich, vielseitig
- `af_heart`: Weiblich, warm
- `af_sky`: Weiblich, klar
- `af_nova`: Weiblich, modern
- `af_alloy`: Weiblich, neutral
- `af_onyx`: Männlich, tief
- `af_echo`: Männlich, resonant
- `af_fable`: Männlich, erzählend
- `af_shimmer`: Weiblich, hell

## Performance-Optimierung

### Engine-Vergleich
```bash
# Performance-Test ausführen
cd backend
python3 test_tts_system.py

# Ergebnisse vergleichen:
# - Piper: Höhere Qualität, deutsche Stimmen, ~100-200ms
# - Kokoro: Kompakter, mehrsprachig, ~50-150ms
```

### Optimierungs-Tipps

1. **Piper für Deutsche Texte**: Bessere Aussprache deutscher Wörter
2. **Kokoro für Englische Texte**: Natürlichere englische Stimmen
3. **Kurze Texte**: Kokoro meist schneller
4. **Lange Texte**: Piper oft gleichwertig
5. **Offline-Betrieb**: Beide Engines funktionieren offline

## Troubleshooting

### Häufige Probleme

#### Kokoro-Modelle nicht gefunden
```bash
# Modelle manuell herunterladen
mkdir -p ~/.local/share/kokoro
cd ~/.local/share/kokoro

wget https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.int8.onnx
wget https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
```

#### Piper-Stimme nicht verfügbar
```bash
# Stimmen-Modelle prüfen
ls ~/.local/share/piper/
piper --list-voices
```

#### Engine-Switching funktioniert nicht
```python
# Debug-Informationen
await manager.get_available_engines()
await manager.test_all_engines()
```

#### Import-Fehler
```bash
# Abhängigkeiten installieren
pip install kokoro-onnx soundfile
pip install faster-whisper
```

### Log-Dateien

```bash
# Backend-Logs
tail -f archive/legacy_ws_server/logs/ws-server.log

# TTS-spezifische Logs
tail -f ~/.local/share/kokoro/logs/
```

### Debug-Modus

```python
# Logging aktivieren
import logging
logging.basicConfig(level=logging.DEBUG)

# Oder in der Konfiguration
StreamingConfig(
    debug_mode=True,
    verbose_logging=True
)
```

## Entwicklung

### Neue TTS-Engine hinzufügen

1. **Engine-Klasse erstellen**:
```python
from backend.tts import BaseTTSEngine, TTSConfig, TTSResult

class MyTTSEngine(BaseTTSEngine):
    async def initialize(self) -> bool:
        # Engine initialisieren
        pass
        
    async def synthesize(self, text: str, voice=None, **kwargs) -> TTSResult:
        # Text zu Audio konvertieren
        pass
```

2. **Manager registrieren**:
```python
# In tts_manager.py TTSEngineType erweitern
class TTSEngineType(Enum):
    PIPER = "piper"
    KOKORO = "kokoro"
    MY_ENGINE = "my_engine"  # Neu
```

3. **Integration testen**:
```python
# Test-Case hinzufügen
await manager.test_all_engines()
```

### API erweitern

```python
# Neue WebSocket-Nachrichten in ws-server-with-tts-switching.py
async def _handle_message(self, client_id: str, data: Dict):
    # Neue Message-Types hinzufügen
    elif message_type == 'my_new_tts_command':
        await self._handle_my_new_command(client_id, data)
```

## Referenz

### Klassen-Übersicht

- `BaseTTSEngine`: Basis-Klasse für alle TTS-Engines
- `PiperTTSEngine`: Piper TTS Implementation
- `KokoroTTSEngine`: Kokoro TTS Implementation
- `TTSManager`: Manager für Engine-Switching
- `TTSConfig`: Konfiguration für TTS-Engines
- `TTSResult`: Ergebnis einer TTS-Synthese

### Konfiguration

- `StreamingConfig`: Server-Konfiguration
- `TTSEngineType`: Verfügbare Engine-Typen
- WebSocket-Nachrichten für TTS-Steuerung

### Tests

- `test_tts_system.py`: Umfassende Test-Suite
- `backend/tts/__init__.py`: Modul-API
- Installationsskripts in `scripts/`

---

*Letzte Aktualisierung: $(date)*
