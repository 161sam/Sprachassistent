import asyncio
import sys
import types

import ws_server.tts.manager as tts_manager
from backend.tts.base_tts_engine import TTSInitializationError
from ws_server.tts.manager import TTSConfig, TTSManager, TTSEngineType


class FakePiper:
    def __init__(self, config):
        self.config = config

    async def initialize(self):
        return True

    async def synthesize(self, text, voice=None, **kwargs):
        class R:
            success = True
            audio_data = b"x"
            engine_used = "piper"
            error_message = None
            processing_time_ms = 0.0
        return R()

    async def cleanup(self):
        pass

    def get_available_voices(self):
        return ["default"]

    def get_engine_info(self):
        return {"name": "fake"}


class FakeZonos:
    def __init__(self, config):
        self.config = config

    async def initialize(self):
        raise TTSInitializationError("missing model")


# Stub-Module in sys.modules eintragen
fake_piper_mod = types.ModuleType("fake_piper")
fake_piper_mod.FakePiper = FakePiper
sys.modules["fake_piper"] = fake_piper_mod

fake_zonos_mod = types.ModuleType("fake_zonos")
fake_zonos_mod.FakeZonos = FakeZonos
sys.modules["fake_zonos"] = fake_zonos_mod


def test_fallback_to_piper_when_zonos_missing(monkeypatch):
    monkeypatch.setattr(
        tts_manager,
        "ENGINE_IMPORTS",
        {
            "piper": ("fake_piper", "FakePiper"),
            "zonos": ("fake_zonos", "FakeZonos"),
        },
        raising=False,
    )
    mgr = TTSManager()
    p_cfg = TTSConfig(engine_type="piper")
    z_cfg = TTSConfig(engine_type="zonos")
    init_ok = asyncio.run(
        mgr.initialize(piper_config=p_cfg, zonos_config=z_cfg, default_engine=TTSEngineType.ZONOS)
    )
    assert init_ok is True
    assert mgr.default_engine == "piper"
    assert "zonos" in mgr.unavailable_engines
    res = asyncio.run(mgr.synthesize("hi"))
    assert res.engine_used == "piper"
