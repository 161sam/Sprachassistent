#!/usr/bin/env python3
"""
Unified server entrypoint:
- Wrappt Legacy VoiceServer
- Hängt Binary-Audio-Unterstützung & Metrics über die neuen Module an
"""
import sys


def _block_legacy_path() -> None:
    """Verhindert Importe aus dem alten ``backend/ws-server`` Pfad."""
    token = "backend/ws-server"
    for name, mod in list(sys.modules.items()):
        file = getattr(mod, "__file__", "") or ""
        if token in file.replace("\\", "/"):
            raise RuntimeError(f"Legacy-Modul nicht erlaubt: {file}")

    class _Finder:
        def find_spec(self, fullname, path, target=None):  # type: ignore[override]
            if fullname.startswith("backend.ws_server"):
                raise ModuleNotFoundError("backend/ws-server ist veraltet")
            return None

    if not any(isinstance(f, _Finder) for f in sys.meta_path):
        sys.meta_path.insert(0, _Finder())


_block_legacy_path()

from ws_server.compat import legacy_ws_server as ws_server_legacy  # noqa: E402

# Export der Legacy-VoiceServer-Klasse für Kompatibilität
VoiceServer = ws_server_legacy.VoiceServer

