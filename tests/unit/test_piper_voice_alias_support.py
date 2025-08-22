import sys
import types

from backend.tts.base_tts_engine import TTSConfig


def test_piper_supports_alias(monkeypatch):
    fake_piper = types.ModuleType("piper")
    fake_piper.PiperVoice = type("PiperVoice", (), {})
    fake_piper.SynthesisConfig = type("SynthesisConfig", (), {})
    sys.modules["piper"] = fake_piper

    from backend.tts.piper_tts_engine import PiperTTSEngine

    engine = PiperTTSEngine(TTSConfig(engine_type="piper", voice="de-thorsten-low"))
    assert engine.supports_voice("de-thorsten-low")
    assert engine.supports_voice("de_DE-thorsten-low")
