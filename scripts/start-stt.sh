#!/usr/bin/env bash
DIR="$(cd "$(dirname "$0")/.." && pwd)"
echo "🧠 Starte STT/TTS WebSocket-Server..."
python3 "$DIR/ws-server/ws-server.py" 2>&1 | tee "$DIR/ws-server.log"

