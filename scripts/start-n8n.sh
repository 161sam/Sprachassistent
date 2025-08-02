#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
[ -f "$SCRIPT_DIR/../.env.n8n" ] && source "$SCRIPT_DIR/../.env.n8n"

HOST="${N8N_HOST:-0.0.0.0}"
PORT="${N8N_PORT:-5678}"

echo "🚀 Starte n8n auf $HOST:$PORT..."

if [ "${N8N_DOCKER:-false}" = "true" ]; then
  docker run -d --name n8n -p "${PORT}:5678" -e N8N_HOST="$HOST" -e N8N_PORT="$PORT" -e N8N_BASIC_AUTH_ACTIVE=true -e N8N_BASIC_AUTH_USER=admin -e N8N_BASIC_AUTH_PASSWORD="${N8N_API_KEY}" n8nio/n8n
else
  n8n start --host "$HOST" --port "$PORT"
fi
