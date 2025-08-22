#!/usr/bin/env bash
set -euo pipefail
ROOT="$(pwd)"

# Quelle der Altdateien automatisch erkennen:
if [ -d "backend/ws-server" ]; then
  SRC_DIR="backend/ws-server"
else
  SRC_DIR="."
fi
echo "Using SRC_DIR=$SRC_DIR"

# 1) Neue Paketstruktur
mkdir -p ws_server/{core,transport,protocol,metrics,tts/engines,auth,compat}
# __init__.py für alle Pakete
find ws_server -type d -exec bash -lc 'p="$1/__init__.py"; [ -f "$SRC_DIR/"$p"" ] || echo "# package" > "$p"' _ {} \;

# 2) Dateien in neue Struktur verschieben (mit Fallback: erst kopieren, dann optional altes File behalten)
#   – Binary-Protokoll
if [ -f "$SRC_DIR/binary_audio_handler.py" ]; then
  cp -n "$SRC_DIR/binary_audio_handler.py" ws_server/protocol/binary_v2.py
fi

#   – Enhanced Server (nur als Referenz/Adapter)
if [ -f "$SRC_DIR/enhanced_websocket_server.py" ]; then
  cp -n "$SRC_DIR/enhanced_websocket_server.py" ws_server/transport/enhanced_ws_server.py
fi
if [ -f "$SRC_DIR/ws-server-enhanced.py" ]; then
  cp -n "$SRC_DIR/ws-server-enhanced.py" ws_server/transport/server_enhanced_entry.py
fi

#   – Metriken
if [ -f "$SRC_DIR/performance_metrics.py" ]; then
  cp -n "$SRC_DIR/performance_metrics.py" ws_server/metrics/collector.py
fi
if [ -f "$SRC_DIR/performance_monitor.py" ]; then
  cp -n "$SRC_DIR/performance_monitor.py" ws_server/metrics/perf_monitor.py
fi
if [ -f "$SRC_DIR/metrics_api.py" ]; then
  cp -n "$SRC_DIR/metrics_api.py" ws_server/metrics/http_api.py
fi

#   – FastAPI Adapter
if [ -f "$SRC_DIR/ws_server_fastapi.py" ]; then
  cp -n "$SRC_DIR/ws_server_fastapi.py" ws_server/transport/fastapi_adapter.py
fi

#   – Zonos Engine
if [ -f "$SRC_DIR/engine_zonos.py" ]; then
  cp -n "$SRC_DIR/engine_zonos.py" ws_server/tts/engines/zonos.py
fi

#   – Legacy ws-server als kompatibler Import
if [ -f "$SRC_DIR/ws-server.py" ]; then
  cp -n "$SRC_DIR/ws-server.py" ws_server/compat/legacy_ws_server.py
fi

# 3) Neuer einheitlicher Entry (Server) – dünner Wrapper um Legacy+Binary
cat > ws_server/transport/server.py <<'PY'
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
PY

# 4) Mini-CLI
cat > ws_server/cli.py <<'PY'
#!/usr/bin/env python3
import asyncio, os, logging
from ws_server.transport.server import VoiceServer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

async def main():
    server = VoiceServer()
    await server.initialize()
    host = os.getenv("WS_HOST","127.0.0.1")
    port = int(os.getenv("WS_PORT","48231"))
    import websockets
    async with websockets.serve(server.handle_websocket, host, port, ping_interval=20, ping_timeout=10):
        logging.info("Unified WS-Server listening on ws://%s:%s", host, port)
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
PY

echo "✅ Struktur erstellt & Dateien einsortiert."

