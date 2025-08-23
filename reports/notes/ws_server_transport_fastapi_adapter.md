# ws_server/transport/fastapi_adapter.py

## Design Notes
- Provide FastAPI application so HTTP clients can reuse WebSocket server logic.
- Expose `create_app()` factory accepting optional `VoiceServer` for testability.
- Implement minimal `WebSocketAdapter` translating FastAPI WebSocket into expected interface.
- Basic token verification via `WS_TOKEN` env var (default `devsecret`).
- Startup event initializes the provided `VoiceServer`.
- WebSocket endpoint delegates handling to `VoiceServer.handle_websocket`.
