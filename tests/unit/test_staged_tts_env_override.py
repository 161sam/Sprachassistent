import asyncio
from ws_server.tts.staged_tts.staged_processor import StagedTTSProcessor, StagedTTSConfig


class OnlyZonosManager:
    engines = {"zonos": type("E", (), {"is_initialized": True})()}

    async def synthesize(self, text, engine=None, voice=None):
        if engine != "zonos":
            raise ValueError("engine not available")

        class R:
            success = True
            audio_data = b"x"
            engine_used = engine
            error_message = None
            sample_rate = 22050
            audio_format = "wav"

        await asyncio.sleep(0)
        return R()

    def engine_allowed_for_voice(self, engine, voice):
        return True


def test_env_intro_override_skips_unavailable_engine(monkeypatch):
    monkeypatch.setenv("STAGED_TTS_INTRO_ENGINE", "piper")
    proc = StagedTTSProcessor(OnlyZonosManager(), StagedTTSConfig())
    text = "Hallo Welt. " * 20
    chunks = asyncio.run(proc.process_staged_tts(text, "de-thorsten-low"))
    assert len(chunks) >= 1
    assert all(c.engine == "zonos" for c in chunks)
