# Unified WebSocket Server

The voice assistant backend exposes a single server entrypoint.  Run it
from the project root:

```bash
python -m ws_server.cli
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

## Protocol

Clients connect via WebSocket.  A `hello` message is exchanged during the
handshake, followed by JSON messages or binary audio frames.

## Health & Metrics

Metrics and a simple health check are exposed over HTTP on
`http://127.0.0.1:$METRICS_PORT/metrics` and `.../health` once the server
is running.

