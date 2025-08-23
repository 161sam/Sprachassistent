import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from ws_server.transport.fastapi_adapter import create_app


class DummyVoiceServer:
    def __init__(self) -> None:
        self.initialized = False
        self.handled = False

    async def initialize(self) -> None:
        self.initialized = True

    async def handle_websocket(self, ws, path="/ws") -> None:  # pragma: no cover - dummy
        self.handled = True
        await ws.send("pong")


def test_websocket_accepts_valid_token(monkeypatch):
    vs = DummyVoiceServer()
    app = create_app(vs)
    monkeypatch.setenv("WS_TOKEN", "secret")
    with TestClient(app) as client:
        with client.websocket_connect("/ws?token=secret") as ws:
            assert ws.receive_text() == "pong"
    assert vs.initialized and vs.handled


def test_websocket_rejects_invalid_token(monkeypatch):
    vs = DummyVoiceServer()
    app = create_app(vs)
    monkeypatch.setenv("WS_TOKEN", "secret")
    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws?token=wrong"):
                pass
