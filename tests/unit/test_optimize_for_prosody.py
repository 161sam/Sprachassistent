from ws_server.tts.staged_tts.chunking import optimize_for_prosody


def test_optimize_for_prosody_removes_diacritics():
    assert optimize_for_prosody('façade') == 'facade.'
