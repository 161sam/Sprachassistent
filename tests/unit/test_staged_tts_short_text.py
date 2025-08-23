import asyncio

from ws_server.tts.staged_tts.staged_processor import StagedTTSProcessor, StagedTTSConfig


class OnlyZonosManager:
    engines = {"zonos": object()}

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
        return engine == "zonos"


def test_short_text_without_intro_engine_uses_main_engine():
    proc = StagedTTSProcessor(
        OnlyZonosManager(),
        StagedTTSConfig(max_intro_length=50, max_chunks=3),
    )
    text = "Hallo Welt"
    chunks = asyncio.run(proc.process_staged_tts(text, "de-thorsten-low"))
    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.engine == "zonos"
    assert chunk.index == 0
    assert chunk.total == 1
    assert chunk.text.startswith(text)
