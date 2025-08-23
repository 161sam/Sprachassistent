import os
import asyncio
from pathlib import Path

from backend.tts.piper_tts_engine import PiperTTSEngine
from backend.tts.base_tts_engine import TTSConfig


def test_initialize_with_relative_models_dir(monkeypatch, tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    models_dir = tmp_path / "alt_models" / "piper"
    models_dir.mkdir(parents=True)
    # engine resolves canonical filenames like "de_DE-thorsten-low.onnx"
    # ensure the mapping can locate the model
    (models_dir / "de_DE-thorsten-low.onnx").write_bytes(b"0")
    (models_dir / "de_DE-thorsten-low.onnx.json").write_text("{}")

    rel_path = os.path.relpath(models_dir.parent, start=repo_root)
    monkeypatch.setenv("MODELS_DIR", rel_path)
    # TTS_MODEL_DIR overrides MODELS_DIR; ensure both point to our temp tree
    monkeypatch.setenv("TTS_MODEL_DIR", rel_path)

    cfg = TTSConfig(engine_type="piper", voice="de-thorsten-low")
    engine = PiperTTSEngine(cfg)
    assert asyncio.run(engine.initialize()) is True
    assert Path(engine.config.model_path).resolve() == (
        models_dir / "de_DE-thorsten-low.onnx"
    ).resolve()
