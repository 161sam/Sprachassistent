import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "voice_aliases", Path(__file__).resolve().parents[2] / "backend" / "tts" / "voice_aliases.py"
)
voice_aliases = importlib.util.module_from_spec(spec)
spec.loader.exec_module(voice_aliases)  # type: ignore
resolve_voice_alias = voice_aliases.resolve_voice_alias

def test_resolve_voice_alias():
    assert resolve_voice_alias("de-thorsten-low") == "de_DE-thorsten-low"
    assert resolve_voice_alias("de_DE-thorsten-low") == "de_DE-thorsten-low"
    assert resolve_voice_alias("unknown") == "unknown"
