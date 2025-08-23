import asyncio
import io
import wave

from backend.tts.base_tts_engine import TTSResult
from ws_server.tts.staged_tts.staged_processor import StagedTTSProcessor, StagedTTSConfig


class DummyManager:
    def __init__(self, piper_available=True):
        self.engines = {}
        if piper_available:
            self.engines["piper"] = type("E", (), {"is_initialized": True})()
        self.engines["zonos"] = type("E", (), {"is_initialized": True})()

    async def synthesize(self, text, engine=None, voice=None):
        sr = 22050 if engine == "piper" else 16000
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(b"\x00\x01" * 20)
        return TTSResult(
            audio_data=buf.getvalue(),
            success=True,
            sample_rate=sr,
            engine_used=engine,
            audio_format="wav",
        )

    def engine_allowed_for_voice(self, engine, voice):
        return True


def test_plan_intro_piper_main_zonos(monkeypatch):
    monkeypatch.setenv("STAGED_TTS_INTRO_ENGINE", "piper")
    monkeypatch.setenv("STAGED_TTS_MAIN_ENGINE", "zonos")
    mgr = DummyManager()
    proc = StagedTTSProcessor(mgr, StagedTTSConfig(enable_caching=False))
    plan = proc._resolve_plan("de-thorsten-low")
    assert plan.intro_engine == "piper"
    assert plan.main_engine == "zonos"
    text = "Hallo Welt. " * 20
    chunks = asyncio.run(proc.process_staged_tts(text, "de-thorsten-low"))
    assert chunks[0].engine == "piper"
    assert all(c.engine == "zonos" for c in chunks[1:])


def test_plan_falls_back_to_zonos(monkeypatch):
    monkeypatch.setenv("STAGED_TTS_INTRO_ENGINE", "piper")
    monkeypatch.setenv("STAGED_TTS_MAIN_ENGINE", "zonos")
    mgr = DummyManager(piper_available=False)
    proc = StagedTTSProcessor(mgr, StagedTTSConfig(enable_caching=False))
    plan = proc._resolve_plan("de-thorsten-low")
    assert plan.intro_engine is None
    assert plan.main_engine == "zonos"
    chunks = asyncio.run(proc.process_staged_tts("Hallo Welt", "de-thorsten-low"))
    assert all(c.engine == "zonos" for c in chunks)
