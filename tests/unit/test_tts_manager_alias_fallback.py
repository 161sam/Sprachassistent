from ws_server.tts.manager import TTSManager
from ws_server.tts.voice_aliases import EngineVoice


def test_engine_allowed_for_voice_alias_fallback(monkeypatch):
    mgr = TTSManager()
    alias_map = {
        "de_DE-thorsten-low": {"zonos": EngineVoice(voice_id="thorsten", language="de")}
    }
    monkeypatch.setattr("backend.tts.tts_manager.VOICE_ALIASES", alias_map)
    assert mgr.engine_allowed_for_voice("zonos", "de_DE-thorsten-low") is True
    assert mgr.engine_allowed_for_voice("piper", "de_DE-thorsten-low") is False
