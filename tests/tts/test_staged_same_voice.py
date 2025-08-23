import asyncio
import io
import wave

from backend.tts.base_tts_engine import TTSResult
from ws_server.tts.staged_tts.staged_processor import StagedTTSProcessor, StagedTTSConfig


class DummyManager:
    async def synthesize(self, text, engine=None, voice=None):
        sr = 22050 if engine == 'piper' else 16000
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(b'\x00\x01' * 20)
        return TTSResult(audio_data=buf.getvalue(), success=True, sample_rate=sr, engine_used=engine, audio_format='wav')

    def engine_allowed_for_voice(self, engine, voice):
        return True

    engines = {"piper": object(), "zonos": object()}
def test_intro_piper_main_zonos_sr_ok():
    mgr = DummyManager()
    proc = StagedTTSProcessor(mgr, StagedTTSConfig(enable_caching=False))
    chunks = asyncio.run(proc.process_staged_tts("Hallo Welt", "de-thorsten-low"))
    assert chunks[0].engine == 'piper'
    assert chunks[0].audio_data
    with wave.open(io.BytesIO(chunks[0].audio_data), 'rb') as wf:
        assert wf.getframerate() == 22050
        assert wf.getnframes() > 0
