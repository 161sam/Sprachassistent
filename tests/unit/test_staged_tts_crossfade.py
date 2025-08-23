from ws_server.tts.staged_tts.staged_processor import StagedTTSProcessor, TTSChunk
import io
import numpy as np
import soundfile as sf


class DummyManager:
    pass


def test_crossfade_env_override(monkeypatch):
    monkeypatch.setenv("STAGED_TTS_CROSSFADE_MS", "250")
    proc = StagedTTSProcessor(DummyManager())

    # generate tiny valid wav (silence)
    buf = io.BytesIO()
    sf.write(buf, np.zeros(22050, dtype=np.float32), 22050, format="WAV", subtype="PCM_16")
    audio_bytes = buf.getvalue()

    chunk = TTSChunk("x", 0, 1, "piper", "hi", audio_bytes, True, 22050)
    msg = proc.create_chunk_message(chunk)
    assert msg["crossfade_ms"] == 250
    assert msg["op"] == "staged_tts_chunk"
    assert msg["format"] == "f32"
    assert msg["pcm"]
