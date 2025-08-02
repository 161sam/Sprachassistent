#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
[ -f "$SCRIPT_DIR/../.env.flowise" ] && source "$SCRIPT_DIR/../.env.flowise"

echo "🔁 Installiere Flowise..."

if [ "${FLOWISE_DOCKER:-false}" = "true" ]; then
  docker pull flowiseai/flowise
else
  sudo apt update && sudo apt install -y nodejs npm
  sudo npm install -g flowise
fi

echo "✅ Flowise Installation abgeschlossen"
