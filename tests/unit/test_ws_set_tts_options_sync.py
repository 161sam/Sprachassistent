import json
import types
import pytest

from ws_server.transport.fastapi_adapter import _handle_gui_control, TTS_OPTIONS_STATE


class DummyWS:
    def __init__(self):
        self.sent = []

    async def send_text(self, s: str):
        self.sent.append(s)


@pytest.mark.asyncio
async def test_set_tts_options_sync_updates_state_and_replies_ok():
    ws = DummyWS()
    payload = {"type": "set_tts_options", "engine": "zonos", "speed": 1.0}
    ok = await _handle_gui_control(ws, payload)
    assert ok is True
    # no exception and reply ok present
    assert any(json.loads(m).get("type") == "ok" and json.loads(m).get("action") == "set_tts_options" for m in ws.sent)
    # state stored synchronously
    assert TTS_OPTIONS_STATE.get("engine") == "zonos"
    assert float(TTS_OPTIONS_STATE.get("speed")) == 1.0

