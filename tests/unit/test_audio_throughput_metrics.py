import asyncio
import time

from ws_server.metrics.collector import collector
from ws_server.protocol.binary_v2 import BinaryAudioHandler, build_audio_frame
from ws_server.tts.staged_tts.staged_processor import TTSChunk, StagedTTSProcessor


class _StubWebSocket:
    async def send(self, _data):
        pass


class _StubSTT:
    sample_rate = 16000
    channels = 1

    async def process_binary_audio(self, _data, stream_id, sequence):
        return None


async def _handle_audio_frame():
    handler = BinaryAudioHandler()
    frame = build_audio_frame("stream", 1, time.time(), b"\x00\x00" * 10)
    await handler.handle_binary_message(_StubWebSocket(), frame, _StubSTT(), object())


def test_audio_in_bytes_metric():
    collector.audio_in_bytes_total._value.set(0)
    asyncio.run(_handle_audio_frame())
    assert collector.audio_in_bytes_total._value.get() == 20


def test_audio_out_bytes_metric():
    collector.audio_out_bytes_total._value.set(0)
    chunk = TTSChunk(
        sequence_id="seq",
        index=0,
        total=1,
        engine="piper",
        text="hi",
        audio_data=b"12345678",
        success=True,
    )
    proc = StagedTTSProcessor(object())
    proc.create_chunk_message(chunk)
    assert collector.audio_out_bytes_total._value.get() == 8
