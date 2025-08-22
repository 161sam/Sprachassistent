# Staged TTS Implementation - Dokumentation

## Übersicht

Das Staged TTS System implementiert einen zweistufigen Ansatz für Text-to-Speech, der die Benutzererfahrung durch sofortiges Audio-Feedback und hochwertige Hauptausgabe verbessert.

## Funktionsweise

### Stage A: Piper Intro (CPU, schnell)
- Erste 120 Zeichen des Texts
- Verwendet Piper TTS Engine (CPU-basiert)
- Wird sofort generiert und gesendet
- Bietet unmittelbares Audio-Feedback

### Stage B: Zonos Hauptinhalt (GPU, hochwertig)
- Restlicher Text in 80-180 Zeichen Chunks
- Verwendet Zonos TTS Engine (GPU-basiert)
- Wird parallel zum Intro verarbeitet
- Liefert hochwertige Audio-Ausgabe

## Konfiguration

### Umgebungsvariablen

```bash
# Staged TTS aktivieren/deaktivieren
STAGED_TTS_ENABLED=true

# Maximale Antwortlänge (Zeichen)
STAGED_TTS_MAX_RESPONSE_LENGTH=500

# Maximale Intro-Länge (Zeichen)
STAGED_TTS_MAX_INTRO_LENGTH=120

# Timeout pro Chunk (Sekunden)
STAGED_TTS_CHUNK_TIMEOUT=10

# Maximale Anzahl Chunks
STAGED_TTS_MAX_CHUNKS=3

# Caching aktivieren
STAGED_TTS_ENABLE_CACHING=true
```

### Zur Laufzeit konfigurieren

Via WebSocket-Message:

```json
{
  "type": "staged_tts_control",
  "action": "configure",
  "config": {
    "max_response_length": 600,
    "max_intro_length": 100,
    "chunk_timeout_seconds": 15,
    "max_chunks": 4,
    "enable_caching": true
  }
}
```

## WebSocket API

### Neue Message-Typen

#### tts_chunk
```json
{
  "type": "tts_chunk",
  "sequence_id": "a1b2c3d4",
  "index": 0,
  "total": 3,
  "engine": "piper",
  "text": "Das ist der Intro-Text...",
  "audio": "data:audio/wav;base64,UklGRnoGAABXQVZFZm10...",
  "success": true,
  "error": null,
  "timestamp": 1692123456.789
}
```

#### tts_sequence_end
```json
{
  "type": "tts_sequence_end",
  "sequence_id": "a1b2c3d4",
  "timestamp": 1692123456.789
}
```

### Kontroll-Commands

#### Status abfragen
```json
{
  "type": "staged_tts_control",
  "action": "get_stats"
}
```

#### Ein-/Ausschalten
```json
{
  "type": "staged_tts_control",
  "action": "toggle"
}
```

#### Cache leeren
```json
{
  "type": "staged_tts_control",
  "action": "clear_cache"
}
```

## Client-seitige Implementierung

### Audio-Playback-Sequencer

- Chunks werden pro `sequence_id` in einer Queue gesammelt.
- `audio.load()` puffert den nächsten Chunk vor, um Lücken zu vermeiden.
- Die Crossfade-Dauer ist frei einstellbar (80–120 ms).

```javascript
class StagedTTSPlayer {
  constructor() {
    this.sequences = new Map();
    this.crossfadeMs = 100;
  }

  handleTTSChunk(message) {
    const { sequence_id, index, total, audio } = message;

    if (!this.sequences.has(sequence_id)) {
      this.sequences.set(sequence_id, { chunks: [], index: 0, ended: false });
    }

    const seq = this.sequences.get(sequence_id);
    const el = new Audio(audio.startsWith('data:') ? audio : `data:audio/wav;base64,${audio}`);
    el.preload = 'auto';
    el.load();
    seq.chunks[index] = el;

    if (index === seq.index) {
      this.playNextChunks(sequence_id);
    }
  }

  handleSequenceEnd({ sequence_id }) {
    const seq = this.sequences.get(sequence_id);
    if (seq) seq.ended = true;
  }

  playAudio(audioEl, prev) {
    // Simple crossfade
    const duration = this.crossfadeMs / 1000;
    audioEl.volume = 0;
    audioEl.play().then(() => {
      this.fade(prev, audioEl, duration);
    });
  }

  fade(prev, next, duration) {
    // ...
  }
}
```

### Settings UI

```html
<div class="staged-tts-controls">
  <label>
    <input type="checkbox" id="staged-tts-enabled"> 
    Staged TTS aktivieren
  </label>
  
  <div class="settings">
    <label>Max Response Length: 
      <input type="range" min="100" max="1000" value="500" id="max-response-length">
    </label>
    
    <label>Max Intro Length: 
      <input type="range" min="50" max="200" value="120" id="max-intro-length">
    </label>
    
    <label>Chunk Timeout (s):
      <input type="range" min="5" max="30" value="10" id="chunk-timeout">
    </label>
    <label>Fast-Start:
      <input type="checkbox" id="fast-start">
    </label>
    <label>Chunk Playback:
      <input type="checkbox" id="chunk-playback">
    </label>
    <label>Crossfade (ms):
      <input type="range" min="80" max="120" value="100" id="crossfade-ms">
    </label>

    <button onclick="clearTTSCache()">Cache leeren</button>
  </div>
</div>
```

## Fallback-Verhalten

Das System verfügt über mehrere Fallback-Mechanismen:

1. **Staging fehlgeschlagen**: Fallback zu einzelner TTS-Synthese
2. **Piper nicht verfügbar**: Verwendung von Zonos für alles
3. **Zonos timeout**: Nur Piper-Intro wird abgespielt
4. **Beide Engines fehlgeschlagen**: Fehler-Response

## Performance-Optimierungen

### Caching
- LRU-Cache für häufige Phrasen
- Cache-Key: `{engine}:{text_hash}`
- Automatische Cache-Größenbegrenzung

### Parallelisierung
- Piper und Zonos laufen parallel
- Asyncio für non-blocking Verarbeitung
- Timeout-Management pro Chunk

### Audio-Streaming
- Prebuffering von Audio-Chunks
- Crossfade zwischen Engine-Wechseln
- Minimale Latenz durch sofortigen Start

## Monitoring & Debugging

### Logs
```
🎭 Staged TTS: enabled
🔧 Piper TTS chunk 0: 0.15s
⚡ Zonos TTS chunk 1: 2.34s
✅ Sent piper chunk 0/3
✅ Sent zonos chunk 1/3
📤 Sent sequence end for a1b2c3d4
```

### Metriken
- Cache Hit Rate
- Durchschnittliche Chunk-Verarbeitungszeit
- Engine-spezifische Performance
- Fallback-Häufigkeit

## Bekannte Limitierungen

1. **GPU-Speicher**: Zonos benötigt ausreichend VRAM
2. **Netzwerk-Latenz**: Chunk-Streaming kann bei schlechter Verbindung hakeln
3. **Engine-Abhängigkeit**: Beide Engines müssen verfügbar sein
4. **Text-Länge**: Sehr kurze Texte profitieren nicht vom Staging

## Troubleshooting

### Häufige Probleme

**Staging wird nicht verwendet**
- Prüfen: `STAGED_TTS_ENABLED=true`
- Prüfen: Keine spezifische Engine im Request
- Logs: "Staged TTS: enabled"

**Nur Piper-Audio hörbar**
- Zonos Engine Status prüfen
- GPU-Verfügbarkeit kontrollieren
- Timeout-Einstellungen erhöhen

**Cache-Probleme**
- Cache mit `staged_tts_control` -> `clear_cache` leeren
- Cache-Statistiken über `get_stats` abrufen

**Performance-Probleme**
- `chunk_timeout_seconds` reduzieren
- `max_chunks` begrenzen
- CPU/GPU-Auslastung monitoring
