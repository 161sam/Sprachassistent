from pathlib import Path

import pytest

from ws_server.tts.voice_aliases import VOICE_ALIASES, _load_jsonc
from ws_server.tts.voice_utils import canonicalize_voice


@pytest.fixture
def load_voice_map() -> dict:
    cfg = Path(__file__).resolve().parents[2] / "config" / "tts.json"
    data = _load_jsonc(cfg)
    return data["voice_map"]


def test_alias_mapping_contains_locale_variant(load_voice_map):
    vm = load_voice_map
    assert "de-thorsten-low" in vm
    assert "de_DE-thorsten-low" in vm
    for eng in ("piper", "zonos"):
        assert eng in vm["de-thorsten-low"]
        assert eng in vm["de_DE-thorsten-low"]

    v = canonicalize_voice("de_DE-thorsten-low")
    assert v in VOICE_ALIASES
