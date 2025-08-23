from types import SimpleNamespace
import sys
import types

from ws_server.tts.voice_aliases import VOICE_ALIASES, EngineVoice


def test_piper_config_missing_model(monkeypatch):
    alias = EngineVoice(model_path="does_not_exist.onnx")
    monkeypatch.setitem(VOICE_ALIASES, "de-test", {"piper": alias})
    cfg = SimpleNamespace(
        default_tts_voice="de-test",
        default_tts_speed=1.0,
        default_tts_volume=1.0,
        tts_model_dir="models",
    )
    # Stub schwergewichtige Abhängigkeiten
    sys.modules.setdefault("faster_whisper", types.ModuleType("faster_whisper")).WhisperModel = object
    sys.modules.setdefault("dotenv", types.ModuleType("dotenv")).load_dotenv = lambda *a, **k: None
    from ws_server.compat.legacy_ws_server import _build_piper_config
    assert _build_piper_config(cfg) is None
