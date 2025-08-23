import asyncio
import contextlib
import pytest

torch = pytest.importorskip("torch")

from backend.tts.engine_zonos import ZonosTTSEngine
from backend.tts.base_tts_engine import TTSConfig

class DummyAutoencoder:
    sampling_rate = 44100
    def decode(self, codes):
        return torch.zeros(1, 1, 10)

class DummyModel:
    autoencoder = DummyAutoencoder()
    def prepare_conditioning(self, cond_dict):
        return cond_dict
    def generate(self, conditioning):
        return torch.zeros(1, 10)
    def parameters(self):
        yield torch.zeros(1)


def test_zonos_engine_sanitizes_text(monkeypatch):
    captured = {}

    async def run():
        engine = ZonosTTSEngine(TTSConfig(voice="test", language="de"))
        engine.model = DummyModel()
        engine.device = "cpu"

        def fake_make_cond_dict(*, text, language, speaker):
            captured['text'] = text
            return {}

        monkeypatch.setattr("backend.tts.engine_zonos.make_cond_dict", fake_make_cond_dict)
        monkeypatch.setattr("torch.autocast", lambda *a, **k: contextlib.nullcontext())

        await engine.synthesize("Hallo ̧", voice_id="test")

    asyncio.run(run())
    assert '̧' not in captured['text']
