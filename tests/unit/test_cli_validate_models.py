import os
import subprocess
import sys


def test_cli_validate_models_lists_aliases(tmp_path):
    piper_dir = tmp_path / "piper"
    piper_dir.mkdir()
    (piper_dir / "de-thorsten-low.onnx").write_bytes(b"0")
    (piper_dir / "de-thorsten-low.onnx.json").write_text("{}")

    env = os.environ.copy()
    env["TTS_MODEL_DIR"] = str(tmp_path)
    result = subprocess.run(
        [sys.executable, "-m", "ws_server.cli", "--validate-models"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert "de-thorsten-low" in result.stdout
