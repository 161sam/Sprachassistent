from pathlib import Path
from ws_server.tts.engines import zonos as zn


def test_find_voice_sample_case_insensitive(tmp_path: Path, monkeypatch):
    # Prepare spk_cache with mixed-case filename
    base = tmp_path / "spk_cache"
    base.mkdir(parents=True, exist_ok=True)
    sample = base / "ThOrStEn.WAV"
    sample.write_bytes(b"RIFF....WAVE")

    # Force speaker dir to tmp
    monkeypatch.setenv("ZONOS_SPEAKER_DIR", str(base))
    repo_root = Path(__file__).resolve().parents[2]
    p = zn._find_voice_sample(repo_root, "thorsten")
    assert p is not None and p.name.lower() == "thorsten.wav"

def test_find_voice_sample_missing(tmp_path: Path, monkeypatch):
    base = tmp_path / "spk_cache"
    base.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("ZONOS_SPEAKER_DIR", str(base))
    repo_root = Path(__file__).resolve().parents[2]
    p = zn._find_voice_sample(repo_root, "thorsten")
    assert p is None

