from pathlib import Path
import pytest

from ws_server.tts.engines.piper import resolve_piper_model


def touch(p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"0")


def write_json(p: Path, sr: int):
    p.write_text('{"sample_rate": %d}' % int(sr), encoding="utf-8")


def test_resolve_prefers_german_when_default(tmp_path: Path):
    models = tmp_path / "models" / "piper"
    touch(models / "en-amy-low.onnx")
    touch(models / "de-thorsten-low.onnx")
    write_json(models / "de-thorsten-low.onnx.json", 22050)
    v, p, sr = resolve_piper_model(None, models)
    assert v.startswith("de-")
    assert p.name == "de-thorsten-low.onnx"
    assert int(sr) == 22050


def test_resolve_specific_voice(tmp_path: Path):
    models = tmp_path / "piper"
    touch(models / "de-thorsten-low.onnx")
    write_json(models / "de-thorsten-low.onnx.json", 24000)
    v, p, sr = resolve_piper_model("de-thorsten-low", models)
    assert v == "de-thorsten-low"
    assert p.name == "de-thorsten-low.onnx"
    assert int(sr) == 24000


def test_resolve_raises_when_missing(tmp_path: Path):
    with pytest.raises(ValueError):
        resolve_piper_model("de-thorsten-low", tmp_path / "models" / "piper")

