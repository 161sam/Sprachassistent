import warnings

def test_staged_processor_emits_deprecation_and_delegates(monkeypatch):
    from ws_server.tts.staged_tts import staged_processor as sp
    calls = {"n": 0}

    async def _stub_synthesize_staged(mgr, text: str, voice: str | None = None):
        calls["n"] += 1
        return (b"\x00\x00\x00\x00", 24000)

    monkeypatch.setenv("STAGED_TTS_CROSSFADE_MS", "120")
    monkeypatch.setattr("ws_server.tts.staged_tts.adapter.synthesize_staged", _stub_synthesize_staged, raising=False)

    proc = sp.StagedTTSProcessor(manager=None)
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always", DeprecationWarning)
        chunks = __import__("asyncio").get_event_loop().run_until_complete(
            proc.process_staged_tts("Hallo Welt", "de-thorsten-low")
        )
        assert any(isinstance(w.message, DeprecationWarning) for w in rec)
    assert calls["n"] == 1
    assert isinstance(chunks, list) and len(chunks) == 1
