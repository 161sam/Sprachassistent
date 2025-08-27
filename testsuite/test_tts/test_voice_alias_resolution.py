import pytest

from ws_server.tts.manager import TTSManager


def test_resolve_known_engines():
    mgr = TTSManager()
    ev_piper = mgr._resolve_engine_voice("piper", "de-thorsten-low")
    assert ev_piper.model_path.endswith("de_DE-thorsten-low.onnx")
    ev_zonos = mgr._resolve_engine_voice("zonos", "de-thorsten-low")
    assert ev_zonos.voice_id == "thorsten"


def test_missing_engine_mapping_raises():
    mgr = TTSManager()
    with pytest.raises(ValueError):
        mgr._resolve_engine_voice("kokoro", "de-thorsten-low")
