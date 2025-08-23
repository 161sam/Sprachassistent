from ws_server.tts.voice_aliases import VOICE_ALIASES
from ws_server.tts.voice_utils import canonicalize_voice


def test_alias_mapping_contains_locale_variant():
    v = canonicalize_voice('de_DE-thorsten-low')
    assert v in VOICE_ALIASES
    mapping = VOICE_ALIASES[v]
    assert 'piper' in mapping and 'zonos' in mapping
