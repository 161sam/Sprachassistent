import asyncio
from ws_server.tts.staged_tts.staged_processor import StagedTTSProcessor, StagedTTSConfig
from ws_server.metrics.collector import collector


class OnlyPiperManager:
    engines = {"piper": object()}

    async def synthesize(self, text, engine=None, voice=None):
        if engine != "piper":
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
        # advertise support for zonos to trigger fallback logic
        return True


def test_fallback_to_piper_only():
    collector.tts_engine_unavailable_total.labels(engine="zonos")._value.set(0)
    collector.tts_chunk_emitted_total.labels(engine="piper")._value.set(0)
    proc = StagedTTSProcessor(
        OnlyPiperManager(),
        StagedTTSConfig(max_chunks=3, max_intro_length=20),
    )
    text = "Hallo Welt. Noch ein Satz."
    chunks = asyncio.run(proc.process_staged_tts(text, "de-thorsten-low"))
    # zonos chunk fails, piper chunk succeeds
    assert len(chunks) == 2
    assert chunks[0].engine == "piper"
    assert chunks[1].engine == "zonos" and not chunks[1].success
    proc.create_chunk_message(chunks[0])
    assert collector.tts_engine_unavailable_total.labels(engine="zonos")._value.get() == 1
    assert collector.tts_chunk_emitted_total.labels(engine="piper")._value.get() == 1


class TimeoutManager:
    engines = {"piper": object(), "zonos": object()}

    async def synthesize(self, text, engine=None, voice=None):
        class R:
            success = True
            audio_data = b"x"
            engine_used = engine
            error_message = None
            sample_rate = 22050
            audio_format = "wav"

        if engine == "piper":
            await asyncio.sleep(0)
            return R()
        if engine == "zonos":
            await asyncio.sleep(0.2)
            return R()

    def engine_allowed_for_voice(self, engine, voice):
        return True


def test_timeout_counts_metric():
    collector.tts_sequence_timeout_total.labels(engine="zonos")._value.set(0)
    collector.tts_chunk_emitted_total.labels(engine="piper")._value.set(0)
    proc = StagedTTSProcessor(
        TimeoutManager(),
        StagedTTSConfig(chunk_timeout_seconds=0.05, max_chunks=2),
    )
    text = "Hallo Welt. Noch ein Satz. " * 5
    chunks = asyncio.run(proc.process_staged_tts(text, "de-thorsten-low"))
    # Only piper chunk succeeded
    assert any(c.engine == "piper" for c in chunks)
    assert any(c.engine == "zonos" and not c.success for c in chunks)
    for c in chunks:
        if c.engine == "piper":
            proc.create_chunk_message(c)
    assert collector.tts_sequence_timeout_total.labels(engine="zonos")._value.get() == 1
    assert collector.tts_chunk_emitted_total.labels(engine="piper")._value.get() == 1
