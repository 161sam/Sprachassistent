#!/usr/bin/env bash
set -e

### 📦 MASTER-INSTALLER für alle Nodes (Raspi4, Raspi400, Odroid, ws-server)
### 🔐 Alle IPs, Tokens, Modelle etc. werden über .env geladen

source .env

log() {
  echo -e "\033[1;34m[INFO]\033[0m $1"
}

abort() {
  echo -e "\033[1;31m[ABORT]\033[0m $1" && exit 1
}

check_env() {
  for var in RASPI4_HOST RASPI400_HOST ODROID_HOST WS_TOKEN FLOWISE_ID FLOWISE_URL N8N_URL STT_MODEL TTS_MODEL; do
    [ -z "${!var}" ] && abort "Environment variable $var is missing in .env"
  done
}

install_node() {
  local NODE_HOST=$1
  local SCRIPT_PATH=$2

  log "📡 Verbinde zu $NODE_HOST und führe $SCRIPT_PATH aus..."
  scp -r ./scripts $NODE_HOST:/tmp/
  ssh $NODE_HOST "bash /tmp/scripts/$SCRIPT_PATH"
}

apply_configs() {
  local NODE_HOST=$1
  local CONFIG_PATH=$2
  log "⚙️ Übertrage Konfiguration an $NODE_HOST:$CONFIG_PATH"
  scp -r ./config/$CONFIG_PATH $NODE_HOST:/home/pi/voice-assistant-config
}

# ==== START INSTALLATION ====
check_env

log "🌐 Beginne Installation aller Nodes..."

## Raspi 4: STT + TTS
install_node $RASPI4_HOST raspi4/install-raspi4.sh
apply_configs $RASPI4_HOST raspi4

## Raspi 400: GUI
install_node $RASPI400_HOST raspi400/install-raspi400.sh
apply_configs $RASPI400_HOST raspi400

## Odroid: n8n + Flowise
install_node $ODROID_HOST odroid/install-odroid.sh
apply_configs $ODROID_HOST odroid

## WebSocket-Server (lokal)
log "🧠 Starte lokale ws-server Installation..."
bash ./scripts/ws-server/install-ws.sh || abort "Fehler bei ws-server Installation"
sudo cp ./ws-server/ws-server.service /etc/systemd/system/ws-server.service
sudo systemctl daemon-reload && sudo systemctl enable ws-server && sudo systemctl start ws-server

log "✅ Alle Komponenten installiert."
