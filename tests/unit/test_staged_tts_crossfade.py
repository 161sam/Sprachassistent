from ws_server.tts.staged_tts.staged_processor import StagedTTSProcessor, TTSChunk


class DummyManager:
    pass


def test_crossfade_env_override(monkeypatch):
    monkeypatch.setenv("STAGED_TTS_CROSSFADE_MS", "250")
    proc = StagedTTSProcessor(DummyManager())
    chunk = TTSChunk("x", 0, 1, "piper", "hi", b"x", True, 22050)
    msg = proc.create_chunk_message(chunk)
    assert msg["crossfade_ms"] == 250
