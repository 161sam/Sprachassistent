import os
from pathlib import Path

from ws_server.tts.engines.piper import resolve_voice


def test_resolve_voice_symlink(monkeypatch, tmp_path):
    model_dir = tmp_path / "piper"
    model_dir.mkdir(parents=True)
    canonical = model_dir / "de_DE-thorsten-low.onnx"
    canonical.write_bytes(b"0")
    (model_dir / "de-thorsten-low.onnx").symlink_to(canonical.name)
    meta = model_dir / "de_DE-thorsten-low.onnx.json"
    meta.write_text('{"sample_rate": 22050}')
    (model_dir / "de-thorsten-low.onnx.json").symlink_to(meta.name)

    monkeypatch.setenv("TTS_MODEL_DIR", str(tmp_path))
    path, sr = resolve_voice("de-thorsten-low")
    assert path == canonical.resolve()
    assert sr == 22050
