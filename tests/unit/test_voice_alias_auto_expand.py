from ws_server.tts.voice_aliases import _build_aliases


def test_auto_expands_locale_alias(monkeypatch):
    data = {
        "voice_map": {
            "de-thorsten-low": {
                "zonos": {"voice_id": "thorsten", "language": "de"}
            }
        }
    }
    monkeypatch.setattr('ws_server.tts.voice_aliases._load_jsonc', lambda path: data)
    aliases = _build_aliases()
    assert 'de-thorsten-low' in aliases
    assert 'de_DE-thorsten-low' in aliases
