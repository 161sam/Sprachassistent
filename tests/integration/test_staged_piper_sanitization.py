import asyncio
import asyncio
import io
import wave
import unicodedata
from ws_server.tts.staged_tts.staged_processor import StagedTTSProcessor, StagedTTSConfig


def _build_wav(sr: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(b'\x00\x01' * 10)
    return buf.getvalue()


class DummyResult:
    def __init__(self):
        self.success = True
        self.sample_rate = 123
        self.audio_data = _build_wav(self.sample_rate)
        self.error_message = None
        self.audio_format = 'wav'


class DummyManager:
    def __init__(self):
        self.last_text = None
        self.last_result = None

    async def synthesize(self, text, engine=None, voice=None):
        self.last_text = text
        self.last_result = DummyResult()
        return self.last_result


def has_mn(text: str) -> bool:
    return any(unicodedata.category(ch) == 'Mn' for ch in text)


def test_pipeline_pre_clean_piper():
    mgr = DummyManager()
    proc = StagedTTSProcessor(mgr, StagedTTSConfig(enable_caching=False))
    asyncio.run(proc._synthesize_chunk('vo\u0327ila', 'piper', 's', 0, 1, 'de'))
    assert mgr.last_text == 'voila'
    assert not has_mn(mgr.last_text)
    assert mgr.last_result.audio_format == 'wav'
    assert mgr.last_result.sample_rate > 0
