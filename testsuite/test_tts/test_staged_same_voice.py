import asyncio

from ws_server.tts.staged_tts.staged_processor import StagedTTSProcessor, StagedTTSConfig


class DummyManager:
    def __init__(self, allow_zonos: bool):
        self.allow_zonos = allow_zonos
        self.calls = []
        self.engines = {"piper": object()}
        if allow_zonos:
            self.engines["zonos"] = object()

    def engine_allowed_for_voice(self, engine: str, voice: str) -> bool:
        return engine != "zonos" or self.allow_zonos

    async def synthesize(self, text, engine=None, voice=None):
        self.calls.append((engine, voice))
        class R:
            success = True
            audio_data = b"x"
            engine_used = engine
            error_message = None
        return R()


def test_staged_uses_same_voice():
    mgr = DummyManager(allow_zonos=True)
    proc = StagedTTSProcessor(mgr, StagedTTSConfig())
    text = "Hallo Welt. Noch ein Satz. " * 5
    asyncio.run(proc.process_staged_tts(text, "de-thorsten-low"))
    voices = {v for _, v in mgr.calls}
    assert voices == {"de-thorsten-low"}
    engines = {e for e, _ in mgr.calls}
    assert "piper" in engines and "zonos" in engines


def test_staged_skips_unmapped_engine():
    mgr = DummyManager(allow_zonos=False)
    proc = StagedTTSProcessor(mgr, StagedTTSConfig())
    text = "Hallo Welt. Noch ein Satz. " * 5
    asyncio.run(proc.process_staged_tts(text, "de-thorsten-low"))
    engines = {e for e, _ in mgr.calls}
    assert engines == {"piper"}
