import os
import logging
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException, status
from fastapi.responses import JSONResponse

from ws_server.transport.server import VoiceServer
from pathlib import Path

from .auth.token_utils import verify_token

# Hinweis: Dieser Adapter bindet ``ws-server.py`` in FastAPI ein.
_legacy_path = Path(__file__).with_name("ws-server.py")
assert spec and spec.loader
# unified import
VoiceServer = VoiceServer

logger = logging.getLogger(__name__)

app = FastAPI()
voice_server = VoiceServer()

ALLOWED_IPS: List[str] = [ip.strip() for ip in os.getenv("ALLOWED_IPS", "").split(",") if ip.strip()]


class WebSocketAdapter:
    """Adapter so the existing server can run on Starlette's WebSocket."""

    def __init__(self, websocket: WebSocket):
        self.websocket = websocket

    @property
    def remote_address(self):
        return (self.websocket.client.host, self.websocket.client.port)

    async def send(self, message: str):
        await self.websocket.send_text(message)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return await self.websocket.receive_text()
        except WebSocketDisconnect:
            raise StopAsyncIteration


@app.on_event("startup")
async def _startup():
    await voice_server.initialize()
    logger.info("FastAPI WebSocket server started")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(None)):
    client_ip = websocket.client.host
    if ALLOWED_IPS and client_ip not in ALLOWED_IPS:
        logger.warning("Unauthorized IP %s", client_ip)
        await websocket.close(code=4401, reason="unauthorized")
        return

    if not verify_token(token):
        await websocket.close(code=4401, reason="unauthorized")
        return

    await websocket.accept()
    adapter = WebSocketAdapter(websocket)
    try:
        await voice_server.handle_websocket(adapter, path="/ws")
    except Exception:
        logging.exception("WebSocket handler crashed")
        try:
            await websocket.send_json({"type": "error", "message": "internal server error"})
        except Exception:
            pass
        await websocket.close(code=1011, reason="server error")


@app.get("/metrics")
async def metrics():
    return JSONResponse(voice_server.get_stats())


@app.post("/debug/restart")
async def restart_endpoint():
    """Restart the underlying voice server for development."""
    try:
        await voice_server.initialize()
        return JSONResponse({"status": "restarted"})
    except Exception as exc:
        logger.error("Restart failed: %s", exc)
        raise HTTPException(status_code=500, detail="restart failed")
