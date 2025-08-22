from pathlib import Path


def test_desktop_uses_unified_entrypoint():
    main_js = Path("voice-assistant-apps/desktop/src/main.js").read_text(encoding="utf-8")
    assert "['-m', 'ws_server.cli']" in main_js
    assert "backend/ws-server/ws-server.py" not in main_js
