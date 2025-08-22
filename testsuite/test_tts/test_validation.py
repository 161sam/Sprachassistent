import dataclasses
from pathlib import Path

from ws_server.tts.voice_aliases import VOICE_ALIASES, EngineVoice
from ws_server.tts.voice_validation import validate_voice_assets


def test_missing_piper_model(monkeypatch, tmp_path):
    missing = tmp_path / "missing.onnx"
    ev = VOICE_ALIASES["de-thorsten-low"]["piper"]
    monkeypatch.setitem(
        VOICE_ALIASES["de-thorsten-low"],
        "piper",
        dataclasses.replace(ev, model_path=str(missing)),
    )
    msgs = validate_voice_assets("de-thorsten-low")
    assert any("Piper model missing" in m for m in msgs)
