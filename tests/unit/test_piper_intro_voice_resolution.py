import os

from ws_server.tts.manager import TTSManager


def test_manager_get_canonical_voice_avoids_default(monkeypatch):
    monkeypatch.setenv("TTS_VOICE", "default")
    monkeypatch.setenv("TTS_DEFAULT_VOICE", "de-thorsten-low")
    m = TTSManager()
    v = m.get_canonical_voice(None)
    assert v == "de-thorsten-low"

