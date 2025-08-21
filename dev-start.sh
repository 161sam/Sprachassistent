#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# Ports freimachen
fuser -k 48231/tcp 48232/tcp 48233/tcp 2>/dev/null || true

export WS_HOST=127.0.0.1 WS_PORT=48231 METRICS_PORT=48232
export JWT_SECRET=${JWT_SECRET:-devsecret}
export JWT_ALLOW_PLAIN=${JWT_ALLOW_PLAIN:-1}
export JWT_BYPASS=${JWT_BYPASS:-0}
export ELECTRON_DISABLE_SANDBOX=1
export ELECTRON_ENABLE_LOGGING=1

echo "▶️  Starting Desktop (will spawn backend) ..."
cd voice-assistant-apps/desktop
npm start
