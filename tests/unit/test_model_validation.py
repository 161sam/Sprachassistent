import importlib.util
from pathlib import Path


spec = importlib.util.spec_from_file_location(
    "model_validation", Path(__file__).resolve().parents[2] / "backend" / "tts" / "model_validation.py"
)
model_validation = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(model_validation)  # type: ignore[assignment]
validate_models = model_validation.validate_models
list_voices_with_aliases = model_validation.list_voices_with_aliases


def test_missing_json_triggers_warning(tmp_path, caplog):
    piper_dir = tmp_path / "piper"
    piper_dir.mkdir()
    (piper_dir / "voice.onnx").write_bytes(b"0")
    validate_models(str(tmp_path))
    assert "Fehlende Datei" in caplog.text


def test_broken_symlink_warns(tmp_path, caplog):
    piper_dir = tmp_path / "piper"
    piper_dir.mkdir()
    target = piper_dir / "missing.onnx"
    (piper_dir / "voice.onnx").symlink_to(target)
    (piper_dir / "voice.onnx.json").write_text("{}")
    validate_models(str(tmp_path))
    assert "Defekter Symlink" in caplog.text


def test_list_voices_with_aliases(tmp_path):
    piper_dir = tmp_path / "piper"
    piper_dir.mkdir()
    (piper_dir / "de_DE-thorsten-low.onnx").write_bytes(b"0")
    (piper_dir / "de_DE-thorsten-low.onnx.json").write_text("{}")
    aliases = list_voices_with_aliases(str(tmp_path))
    assert "de_DE-thorsten-low" in aliases
    assert "de-thorsten-low" in aliases["de_DE-thorsten-low"]
