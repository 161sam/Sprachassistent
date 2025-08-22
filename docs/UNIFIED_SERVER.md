# Unified WebSocket Server

The unified server exposes a single entry point that speaks both JSON v1 and Binary v2 protocols. Clients negotiate the protocol during the initial handshake.

## Start

```bash
python -m ws_server.cli
```

Environment variables such as `WS_HOST`, `WS_PORT` and `METRICS_PORT` configure the ports. The server also exposes an HTTP metrics API on `/metrics` and a health check on `/health`.

## Protocol negotiation

1. Client sends a JSON `hello` message describing its capabilities.
2. Server replies with a feature banner listing supported protocols.
3. If both sides agree on `binary_audio` and it is enabled server side, audio frames are exchanged using Binary v2; otherwise JSON v1 is used.

## Sequence events

Staged TTS emits a stream of events:

- `tts_chunk` – contains `sequence_id`, chunk `index`, `total`, `engine`, `text` and `audio`.
- `tts_sequence_end` – marks the end of a sequence.

## Settings

All options are read from environment variables via the configuration layer:

- `WS_HOST` / `WS_PORT` – WebSocket bind address.
- `METRICS_PORT` – port for `/metrics` and `/health`.
- `ENABLE_BINARY_AUDIO` – enable Binary v2 audio ingress.
- `CHUNK_TTS_TIMEOUT_SEC` – timeout for Zonos TTS chunks.
