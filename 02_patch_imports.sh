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

# 2) Metrics-HTTP-API: interne Importe/Referenzen robust machen (keine Änderung der Logik)
if [ -f ws_server/metrics/http_api.py ]; then
  # Doppelte Imports, sanfte Korrekturen ok – inhaltlich bleibt /metrics,/health,/status gleich.
  sed -i -e '/from aiohttp import web/{x;/./d;x;}' ws_server/metrics/http_api.py || true
fi

echo "✅ Imports/Adapter gepatcht."

