#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
[ -f "$SCRIPT_DIR/../.env.n8n" ] && source "$SCRIPT_DIR/../.env.n8n"

echo "🧠 Installiere n8n..."

if [ "${N8N_DOCKER:-false}" = "true" ]; then
  docker pull n8nio/n8n
else
  sudo apt update && sudo apt install -y nodejs npm
  sudo npm install -g n8n
fi

echo "✅ n8n Installation abgeschlossen"
