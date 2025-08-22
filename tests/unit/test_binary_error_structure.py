import asyncio
import json
from ws_server.protocol.binary_v2 import BinaryAudioHandler


class DummyWebSocket:
    def __init__(self):
        self.data = None
    async def send(self, payload):
        self.data = payload


def test_send_error_structured():
    handler = BinaryAudioHandler()
    ws = DummyWebSocket()
    asyncio.run(handler._send_error(ws, 'test_code', 'oops'))
    msg = json.loads(ws.data)
    assert msg['type'] == 'error'
    assert msg['code'] == 'test_code'
    assert msg['message'] == 'oops'
