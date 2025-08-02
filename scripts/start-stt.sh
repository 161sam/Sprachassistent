#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/.."
[ -f "$ROOT_DIR/.env" ] && source "$ROOT_DIR/.env"
echo "🧠 Starte STT/TTS WebSocket-Server..."
python3 "$ROOT_DIR/ws-server/ws-server.py" 2>&1 | tee "$ROOT_DIR/ws-server.log"

