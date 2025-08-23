import importlib


def test_vad_module_available():
    module = importlib.import_module("ws_server.audio.vad")
    assert hasattr(module, "VoiceActivityDetector")
    assert hasattr(module, "VADConfig")


def test_legacy_audio_alias():
    import sys
    # previous tests may have mocked ``audio.vad``; ensure real module is loaded
    sys.modules.pop("audio", None)
    sys.modules.pop("audio.vad", None)
    alias = importlib.import_module("audio.vad")
    original = importlib.import_module("ws_server.audio.vad")
    assert alias.VoiceActivityDetector is original.VoiceActivityDetector
    assert alias.VADConfig is original.VADConfig
