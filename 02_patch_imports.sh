#!/usr/bin/env bash
set -euo pipefail
[ -d "ws_server" ] || { echo "ws_server/ fehlt. Erst 01_restructure.sh laufen lassen."; exit 1; }

# 1) FastAPI-Adapter: statt dynamisch ws-server.py laden → unified transport server
if [ -f ws_server/transport/fastapi_adapter.py ]; then
  sed -i \
    -e 's|import importlib.util.*$|from ws_server.transport.server import VoiceServer|' \
    -e '/spec = importlib.util.spec_from_file_location/d' \
    -e '/ws_server_legacy = importlib.util.module_from_spec/d' \
    -e '/spec.loader.exec_module(ws_server_legacy)/d' \
    -e 's|VoiceServer = ws_server_legacy.VoiceServer|# unified import\nVoiceServer = VoiceServer|' \
    ws_server/transport/fastapi_adapter.py
fi

# 2) Enhanced-Server: neue Modulpfade für Binary/Metrics
if [ -f ws_server/transport/enhanced_ws_server.py ]; then
  sed -i \
    -e 's|from binary_audio_handler import|from ws_server.protocol.binary_v2 import|g' \
    ws_server/transport/enhanced_ws_server.py
fi
if [ -f ws_server/transport/server_enhanced_entry.py ]; then
  sed -i \
    -e 's|from binary_audio_handler import|from ws_server.protocol.binary_v2 import|g' \
    -e 's|from performance_metrics import|from ws_server.metrics.collector import|g' \
    -e 's|from enhanced_websocket_server import|from ws_server.transport.enhanced_ws_server import|g' \
    ws_server/transport/server_enhanced_entry.py
fi

# 3) Metrics-HTTP-API: interne Importe/Referenzen robust machen (keine Änderung der Logik)
if [ -f ws_server/metrics/http_api.py ]; then
  # Doppelte Imports, sanfte Korrekturen ok – inhaltlich bleibt /metrics,/health,/status gleich.
  sed -i -e '/from aiohttp import web/{x;/./d;x;}' ws_server/metrics/http_api.py || true
fi

echo "✅ Imports/Adapter gepatcht."

