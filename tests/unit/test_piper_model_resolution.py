import types
import pytest

# Provide a minimal stub for the optional 'piper' dependency
class _DummyVoice:
    config = types.SimpleNamespace(sample_rate=22050)
    def synthesize(self, text, syn_config=None):
        yield types.SimpleNamespace(audio_int16_bytes=b"")

class _DummyPiperVoice:
    @staticmethod
    def load(path):
        return _DummyVoice()

sys_modules = {
    "piper": types.SimpleNamespace(PiperVoice=_DummyPiperVoice, SynthesisConfig=object)
}

# Inject stub into sys.modules before importing engine
import sys
sys.modules.update(sys_modules)

from backend.tts.piper_tts_engine import PiperTTSEngine
from backend.tts.base_tts_engine import TTSConfig


def test_piper_initialization_uses_local_model(tmp_path, monkeypatch):
    piper_dir = tmp_path / "piper"
    piper_dir.mkdir()
    model_file = piper_dir / "de-thorsten-low.onnx"
    config_file = piper_dir / "de-thorsten-low.onnx.json"
    model_file.write_bytes(b"")
    config_file.write_text("{}")

    monkeypatch.setenv("TTS_MODEL_DIR", str(tmp_path))
    config = TTSConfig(engine_type="piper", voice="de-thorsten-low", model_dir=str(tmp_path))
    engine = PiperTTSEngine(config)

    import asyncio
    assert asyncio.run(engine.initialize())
    assert engine.config.model_path == str(model_file)
