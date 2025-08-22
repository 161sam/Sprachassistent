#!/usr/bin/env python3
"""
Unified server entrypoint:
- Wrappt Legacy VoiceServer
- Hängt Binary-Audio-Unterstützung & Metrics über die neuen Module an
"""
import importlib.util
from pathlib import Path

# Legacy laden (in-place, ohne Code-Duplikate)
_legacy = Path(__file__).resolve().parents[1] / "compat" / "legacy_ws_server.py"
spec = importlib.util.spec_from_file_location("ws_server_legacy", _legacy)
ws_server_legacy = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(ws_server_legacy)  # type: ignore

# Export der Legacy-VoiceServer-Klasse für Kompatibilität
VoiceServer = ws_server_legacy.VoiceServer
