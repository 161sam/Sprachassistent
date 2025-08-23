"""FastAPI transport adapter for the voice server."""
# TODO: add tests and consider merging into core transport server
#       (see TODO-Index.md: WS-Server / Protokolle)
from __future__ import annotations

import os
from typing import Optional, Protocol

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query


def _verify_token(token: Optional[str]) -> bool:
    expected = os.getenv("WS_TOKEN", "devsecret")
    return token == expected


class VoiceServerLike(Protocol):
    async def initialize(self) -> None: ...
    async def handle_websocket(self, ws, path: str = "/ws") -> None: ...


class _WebSocketAdapter:
    """Bridge FastAPI's WebSocket to the interface expected by ``VoiceServer``."""

    def __init__(self, websocket: WebSocket) -> None:
        self.websocket = websocket

    @property
    def remote_address(self) -> tuple[str, int]:
        client = self.websocket.client
        host = getattr(client, "host", "") if client else ""
        port = getattr(client, "port", 0) if client else 0
        return (host, port)

    async def send(self, message: str) -> None:
        await self.websocket.send_text(message)

    def __aiter__(self) -> "_WebSocketAdapter":
        return self

    async def __anext__(self) -> str:
        try:
            return await self.websocket.receive_text()
        except WebSocketDisconnect as exc:  # pragma: no cover - network disconnect
            raise StopAsyncIteration from exc


def create_app(voice_server: Optional[VoiceServerLike] = None) -> FastAPI:
    """Return a FastAPI app serving the given voice server."""

    if voice_server is None:
        from .server import VoiceServer as _VoiceServer
        vs = _VoiceServer()
    else:
        vs = voice_server
    app = FastAPI()

    @app.on_event("startup")
    async def _startup() -> None:  # pragma: no cover - FastAPI lifecycle
        await vs.initialize()

    @app.websocket("/ws")
    async def _ws_endpoint(websocket: WebSocket, token: Optional[str] = Query(None)) -> None:
        if not _verify_token(token):
            await websocket.close(code=4401, reason="unauthorized")
            return

        await websocket.accept()
        adapter = _WebSocketAdapter(websocket)
        try:
            await vs.handle_websocket(adapter, path="/ws")
        except Exception:  # pragma: no cover - passthrough
            await websocket.close(code=1011, reason="server error")
            raise

    return app


__all__ = ["create_app"]
