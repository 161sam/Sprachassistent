from ws_server.tts.voice_aliases import VOICE_ALIASES, EngineVoice
from ws_server.tts.manager import TTSManager


def test_piper_config_missing_model(monkeypatch):
    alias = EngineVoice(model_path="does_not_exist.onnx")
    monkeypatch.setitem(VOICE_ALIASES, "de-test", {"piper": alias})
    monkeypatch.setenv("TTS_VOICE", "de-test")
    mgr = TTSManager()
    assert mgr._build_piper_config() is None
