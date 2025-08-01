#!/usr/bin/env bash
set -e
source .env

log() {
  echo -e "\033[1;32m[OK]\033[0m $1"
}
fail() {
  echo -e "\033[1;31m[FEHLER]\033[0m $1"
}
check_host() {
  ping -c 1 -W 1 "$1" >/dev/null 2>&1 && log "$1 erreichbar" || fail "$1 nicht erreichbar"
}

check_http() {
  curl -s -o /dev/null "$1" && log "$1 erreichbar" || fail "$1 nicht erreichbar"
}

check_ws_server() {
  echo "{\"token\": \"$WS_TOKEN\"}" | \
    websocat ws://localhost:8123/ --one-message --no-close-stdin >/dev/null 2>&1 && \
    log "WebSocket-Server antwortet" || fail "WebSocket-Server antwortet nicht"
}

echo "🔍 Überprüfe Netzwerkverbindungen und Dienste..."

check_host "$RASPI4_HOST"
check_host "$RASPI400_HOST"
check_host "$ODROID_HOST"

check_http "$FLOWISE_URL"
check_http "$N8N_URL"

if command -v websocat &>/dev/null; then
  check_ws_server
else
  echo -e "\033[1;33m[HINWEIS]\033[0m WebSocket-Test übersprungen – bitte websocat installieren."
fi
