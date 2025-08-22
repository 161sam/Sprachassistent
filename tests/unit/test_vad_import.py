import importlib


def test_vad_module_available():
    module = importlib.import_module("ws_server.audio.vad")
    assert hasattr(module, "VoiceActivityDetector")
    assert hasattr(module, "VADConfig")
