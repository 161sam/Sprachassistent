from ws_server.tts.staged_tts.progress import ProgressRenderer


def test_progress_renderer_no_tty_no_crash_and_format(monkeypatch):
    # Force non-tty to exercise fallback path and capture writes
    writes = []

    class Dummy:
        def isatty(self):
            return False

        def write(self, s):  # noqa: D401
            writes.append(s)

        def flush(self):
            pass

    import sys
    old = sys.stderr
    sys.stderr = Dummy()  # type: ignore
    try:
        pr = ProgressRenderer("intro", total=5, enabled=True)
        pr.update(4)
        pr.done()
    finally:
        sys.stderr = old

    # Expect a line like: "intro: [ ... ]  80% (4/5)" (two spaces before percent width 3)
    out = "".join(writes)
    assert "intro:" in out
    assert " 80% (4/5)" in out
