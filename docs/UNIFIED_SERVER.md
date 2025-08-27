# Unified WebSocket Server

The voice assistant backend exposes a single server entrypoint.  Run it
from the project root:

```bash
python -m ws_server.cli
```

## Quickstart

```bash
pip install -r requirements.txt
cp env.example .env
python -m ws_server.cli
# in another terminal
cd voice-assistant-apps/desktop && npm install && npm start
```

Use `--validate-models` to list detected voices and their aliases without
starting the server:

```bash
python -m ws_server.cli --validate-models
```

## Environment

The server reads configuration from the environment.  Common variables
include:

| Variable | Description |
| --- | --- |
| `WS_HOST` | Bind address for the WebSocket server |
| `WS_PORT` | Port for client connections |
| `METRICS_PORT` | HTTP port for the metrics endpoint |
| `STT_MODEL` | Whisper/Faster-Whisper model name |
| `STT_DEVICE` | Device for STT execution (`cpu`, `cuda`, ...) |
| `TTS_ENGINE` | Default TTS engine (`zonos`, `piper`, ...) |
| `TTS_VOICE` | Default voice identifier |
| `JWT_SECRET` | Shared secret for token verification |

### STT

Incoming PCM16 audio is converted directly into NumPy arrays in memory.
No temporäre WAV-Dateien oder Subprozesse werden genutzt.
Streaming-Unterstützung folgt.

## Protocol

Clients connect via WebSocket.  During the handshake the client sends either
`{"op": "hello"}` or the legacy form `{"type": "hello"}`.  The server
responds with `{"op": "ready", "features": {"binary_audio": true}}` to
advertise binary audio frame support.  After this exchange clients may stream
PCM16 audio either as base64 encoded JSON chunks or as native binary frames.

## Health & Metrics

Metrics and a simple health check are exposed over HTTP on
`http://127.0.0.1:$METRICS_PORT/metrics` and `.../health` once the server
is running.


## Migration: Ablösung `ws_server/compat/legacy_ws_server.py`

- **LLM** → `ws_server/core/llm.py` (LMClient, `list_models()`, `chat()`)
- **Flowise/n8n Bridges** → `ws_server/routing/external.py` (mit Retry/Backoff)
- **AudioChunk/Buffer** → `ws_server/core/streams.py`
- **AudioStreamManager** → `ws_server/transport/audio_streams.py`
- **Transport/Message-Loop** → `ws_server/transport/server.py` (ohne Compat-Import)

Handshake/Loop & Initialisierungslogik wurden aus dem Legacy-Server übernommen und an die Protokoll-Helper (`parse_client_hello()`, `build_ready()`) angeschlossen.
