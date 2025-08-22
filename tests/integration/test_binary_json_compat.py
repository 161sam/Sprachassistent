import base64
import json

import pytest

from ws_server.protocol.binary_v2 import BinaryAudioHandler, build_audio_frame


class DummyWebSocket:
    def __init__(self):
        self.sent: list[str] = []

    async def send(self, msg: str) -> None:  # pragma: no cover - trivial
        self.sent.append(msg)


class StubSTT:
    def __init__(self):
        self.binary_calls = []

    async def process_binary_audio(self, data, stream_id, sequence):
        self.binary_calls.append((stream_id, sequence, data))
        return {"text": "bin"}


class StubMessageHandler:
    def __init__(self):
        self.calls = []

    async def handle_audio_message(self, websocket, data):
        self.calls.append(data)
        return {"text": "json"}


@pytest.mark.asyncio
async def test_binary_and_json_ingress():
    audio = (1).to_bytes(2, "little")  # single PCM16 sample

    # ---- Binary client --------------------------------------------------
    ws = DummyWebSocket()
    stt = StubSTT()
    mh = StubMessageHandler()
    handler = BinaryAudioHandler()
    frame = build_audio_frame("stream", 0, 0.0, audio)
    await handler.handle_binary_message(ws, frame, stt, mh)
    assert stt.binary_calls
    assert json.loads(ws.sent[0])["type"] == "stt_result"

    # ---- JSON fallback client ------------------------------------------
    ws_json = DummyWebSocket()
    mh_json = StubMessageHandler()
    b64 = base64.b64encode(audio).decode("ascii")
    msg = {"stream_id": "j", "chunk": b64, "sequence": 0, "is_binary": False}
    result = await mh_json.handle_audio_message(ws_json, msg)
    assert mh_json.calls[0]["chunk"] == b64
    assert result == {"text": "json"}

    # ---- Binary STT fallback to JSON path ------------------------------
    ws_fb = DummyWebSocket()
    mh_fb = StubMessageHandler()

    class NoBinarySTT:  # lacks process_binary_audio
        pass

    frame_fb = build_audio_frame("fb", 1, 0.0, audio)
    await handler.handle_binary_message(ws_fb, frame_fb, NoBinarySTT(), mh_fb)
    # message handler should have been invoked with base64 encoded data
    assert mh_fb.calls
    assert isinstance(mh_fb.calls[0]["audio_data"], str)
