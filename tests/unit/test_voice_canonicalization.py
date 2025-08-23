from ws_server.tts.voice_utils import canonicalize_voice


def test_canonicalize_voice():
    assert canonicalize_voice("de_DE-thorsten-low") == "de-thorsten-low"
    assert canonicalize_voice(" de_DE-thorsten-low ") == "de-thorsten-low"
    assert canonicalize_voice("de-thorsten-low") == "de-thorsten-low"
