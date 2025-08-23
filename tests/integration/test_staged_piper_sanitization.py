import asyncio
import unicodedata
from ws_server.tts.staged_tts.staged_processor import StagedTTSProcessor, StagedTTSConfig


class DummyResult:
    def __init__(self):
        self.success = True
        self.audio_data = b'a'
        self.error_message = None


class DummyManager:
    def __init__(self):
        self.last_text = None

    async def synthesize(self, text, engine=None, voice=None):
        self.last_text = text
        return DummyResult()


def has_mn(text: str) -> bool:
    return any(unicodedata.category(ch) == 'Mn' for ch in text)


def test_pipeline_pre_clean_piper():
    mgr = DummyManager()
    proc = StagedTTSProcessor(mgr, StagedTTSConfig(enable_caching=False))
    asyncio.run(proc._synthesize_chunk('vo\u0327ila', 'piper', 's', 0, 1, 'de'))
    assert mgr.last_text == 'voila'
    assert not has_mn(mgr.last_text)
