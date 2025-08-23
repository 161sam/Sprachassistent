import os
from pathlib import Path

import pytest

# TODO-FIXED(2024-11-21): require real piper after removing stub
pytest.importorskip("piper")

from ws_server.tts.engines.piper import PiperTTSEngine
from backend.tts.base_tts_engine import TTSConfig


def test_initialize_with_relative_models_dir(monkeypatch, tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    models_dir = tmp_path / "alt_models" / "piper"
    models_dir.mkdir(parents=True)
    # engine resolves canonical filenames like "de_DE-thorsten-low.onnx"
    # ensure the mapping can locate the model
    (models_dir / "de_DE-thorsten-low.onnx").write_bytes(b"0")
    (models_dir / "de_DE-thorsten-low.onnx.json").write_text('{"sample_rate": 12345}')

    rel_path = os.path.relpath(models_dir.parent, start=repo_root)
    monkeypatch.setenv("MODELS_DIR", rel_path)
    # TTS_MODEL_DIR overrides MODELS_DIR; ensure both point to our temp tree
    monkeypatch.setenv("TTS_MODEL_DIR", rel_path)

    cfg = TTSConfig(
        engine_type="piper",
        voice="de-thorsten-low",
        model_path=str(models_dir / "de_DE-thorsten-low.onnx"),
    )
    engine = PiperTTSEngine(cfg)
    engine.sample_rate = engine._read_sample_rate(cfg.model_path)
    assert engine.sample_rate == 12345
    assert Path(engine.config.model_path).resolve() == (
        models_dir / "de_DE-thorsten-low.onnx"
    ).resolve()
