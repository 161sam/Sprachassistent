from pathlib import Path

from backend.tts.base_tts_engine import TTSConfig
from ws_server.tts.engines.piper import PiperTTSEngine


def test_resolve_voice_symlink(tmp_path, monkeypatch):
    models_dir = tmp_path / "models" / "piper"
    models_dir.mkdir(parents=True)
    canonical = models_dir / "de_DE-thorsten-low.onnx"
    canonical.write_bytes(b"0")
    (models_dir / "de_DE-thorsten-low.onnx.json").write_text("{\"sample_rate\":22050}")
    alias = models_dir / "de-thorsten-low.onnx"
    alias.symlink_to(canonical.name)
    (models_dir / "de-thorsten-low.onnx.json").symlink_to("de_DE-thorsten-low.onnx.json")

    monkeypatch.setenv("TTS_MODEL_DIR", str(models_dir))
    cfg = TTSConfig(engine_type="piper", voice="de-thorsten-low")
    engine = PiperTTSEngine(cfg)
    path = engine._resolve_model_path("de-thorsten-low")
    assert Path(path).resolve() == canonical.resolve()
