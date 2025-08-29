import asyncio
import json

import pytest

from ws_server.transport.fastapi_adapter import _handle_gui_control


class DummyWS:
    def __init__(self):
        self.sent = []
        self._tts_runtime = {}

    async def send_text(self, data: str):
        try:
            self.sent.append(json.loads(data))
        except Exception:
            self.sent.append({"raw": data})


@pytest.mark.asyncio
async def test_set_tts_options_sync_handler_stores_runtime_and_returns_ok():
    ws = DummyWS()
    msg = {"type": "set_tts_options", "engine": "piper", "speed": 1.1}
    ok = await _handle_gui_control(ws, msg)
    assert ok is True
    # Check response includes OK action
    assert any(m.get("type") == "ok" and m.get("action") == "set_tts_options" for m in ws.sent)
    # Runtime overrides stored per connection
    assert getattr(ws, "_tts_runtime", {}).get("engine") == "piper"
    assert getattr(ws, "_tts_runtime", {}).get("speed") == pytest.approx(1.1)

