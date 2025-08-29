from ws_server.tts.staged_tts.chunking import limit_and_chunk


def test_chunking_respects_bounds():
    txt = ("Dies ist ein längerer Beispielsatz, der den Chunker testen soll. "
           * 20)
    chunks = limit_and_chunk(txt, max_length=500)
    assert len(" ".join(chunks)) <= 500
    assert all(1 <= len(c) <= 180 for c in chunks)
