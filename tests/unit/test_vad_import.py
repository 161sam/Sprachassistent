import importlib


def test_vad_module_available():
    module = importlib.import_module("ws_server.audio.vad")
    assert hasattr(module, "VoiceActivityDetector")
    assert hasattr(module, "VADConfig")


def test_legacy_audio_alias():
    alias = importlib.import_module("audio.vad")
    original = importlib.import_module("ws_server.audio.vad")
    assert alias.VoiceActivityDetector is original.VoiceActivityDetector
    assert alias.VADConfig is original.VADConfig
