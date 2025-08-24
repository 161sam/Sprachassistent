import unicodedata
import pytest

from ws_server.tts.manager import TTSManager, TTSResult, COMBINING_GUARD_RE


def test_combining_guard_regex_matches():
    assert COMBINING_GUARD_RE.search("a\u0327")


@pytest.mark.asyncio
async def test_manager_strips_combining_before_engine():
    manager = TTSManager()

    class DummyEngine:
        def __init__(self):
            self.last_text = None

        async def synthesize(self, text: str, *args, **kwargs):
            self.last_text = text
            return TTSResult(audio_data=b"", success=True, engine_used="piper")

    dummy = DummyEngine()
    manager.engines["piper"] = dummy
    manager.default_engine = "piper"

    await manager.synthesize("fa\u0327cade", engine="piper")
    assert dummy.last_text == "facade"
    assert all(unicodedata.category(ch) != "Mn" for ch in dummy.last_text)
