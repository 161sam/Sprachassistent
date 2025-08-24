import sys
import types
import asyncio

import ws_server.tts.manager as tts_manager
from ws_server.tts.manager import TTSManager, TTSConfig, TTSEngineType


class FakePiper:
    def __init__(self, config):
        self.config = config
        self.calls = []

    async def initialize(self):
        return True

    async def synthesize(self, text, voice=None, model_path=None, **kwargs):
        self.calls.append(voice)
        class R:
            success = True
            audio_data = b"x"
            engine_used = "piper"
            error_message = None
            processing_time_ms = 0.0
        return R()

    async def set_voice(self, voice):
        self.calls.append(voice)
        return True


def test_tts_manager_passes_voice(monkeypatch):
    fake_mod = types.ModuleType("fake_piper")
    fake_mod.FakePiper = FakePiper
    sys.modules["fake_piper"] = fake_mod
    monkeypatch.setattr(
        tts_manager,
        "ENGINE_IMPORTS",
        {"piper": ("fake_piper", "FakePiper")},
        raising=False,
    )

    mgr = TTSManager()
    p_cfg = TTSConfig(engine_type="piper")
    asyncio.run(mgr.initialize(piper_config=p_cfg, default_engine=TTSEngineType.PIPER))
    asyncio.run(mgr.synthesize("hi", voice="de_DE-thorsten-low"))
    assert mgr.engines["piper"].calls[-1] == "de-thorsten-low"


def test_tts_manager_set_voice_canonicalization(monkeypatch):
    fake_mod = types.ModuleType("fake_piper")
    fake_mod.FakePiper = FakePiper
    sys.modules["fake_piper"] = fake_mod
    monkeypatch.setattr(
        tts_manager,
        "ENGINE_IMPORTS",
        {"piper": ("fake_piper", "FakePiper")},
        raising=False,
    )

    mgr = TTSManager()
    p_cfg = TTSConfig(engine_type="piper")
    asyncio.run(mgr.initialize(piper_config=p_cfg, default_engine=TTSEngineType.PIPER))
    asyncio.run(mgr.set_voice("de_DE-thorsten-low", TTSEngineType.PIPER))
    assert mgr.engines["piper"].calls[-1] == "de-thorsten-low"
