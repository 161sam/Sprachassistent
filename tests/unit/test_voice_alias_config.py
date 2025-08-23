from ws_server.tts.voice_aliases import VOICE_ALIASES, EngineVoice


def test_voice_aliases_loaded_from_config():
    ev = VOICE_ALIASES["de-thorsten-low"]["piper"]
    assert isinstance(ev, EngineVoice)
    assert ev.model_path.endswith("de-thorsten-low.onnx")
