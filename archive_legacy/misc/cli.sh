#!/usr/bin/env bash
set -e

# === Sprachassistent Setup CLI ===
# Nutzt alle vorhandenen Scripts & Konfigurationen

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPTS="$SCRIPT_DIR/scripts"
APPS="$SCRIPT_DIR/voice-assistant-apps"

source "$SCRIPT_DIR/.env" 2>/dev/null || true

GREEN='\033[1;32m'
RED='\033[1;31m'
YELLOW='\033[1;33m'
RESET='\033[0m'

log() { echo -e "${GREEN}[✓]${RESET} $1"; }
warn() { echo -e "${YELLOW}[!]${RESET} $1"; }
fail() { echo -e "${RED}[x]${RESET} $1"; exit 1; }

interactive_env_fill() {
  cp .env.example .env
  echo "✍️  Interaktive Eingabe der .env Variablen..."
  while IFS= read -r line; do
    if [[ "$line" =~ ^[A-Z_]+= ]]; then
      var_name="${line%%=*}"
      default_val="${line#*=}"
      read -p "$var_name [$default_val]: " value
      echo "$var_name=${value:-$default_val}" >> .env.tmp
    fi
  done < .env.example
  mv .env.tmp .env
  echo "✅ .env erfolgreich erstellt."
}

validate_env() {
  REQUIRED_VARS=(WS_TOKEN RASPI4_HOST RASPI400_HOST ODROID_HOST FLOWISE_ID FLOWISE_URL N8N_URL STT_MODEL STT_DEVICE STT_PRECISION TTS_MODEL TTS_SPEED TTS_VOLUME)
  missing=0
  for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then warn "$var fehlt"; missing=1; fi
  done
  [ $missing -eq 1 ] && fail "Fehlende .env Variablen." || log ".env ist vollständig."
}

restart_services() {
  echo "🔁 Starte Dienste neu: ws-server"
  sudo systemctl restart ws-server.service && log "WebSocket-Dienst neu gestartet."
}

backup_configs() {
  stamp=$(date +%Y%m%d_%H%M%S)
  mkdir -p backup
  tar czf backup/configs_$stamp.tar.gz config .env* scripts/*/*.sh ws-server/ws-server.py
  log "📦 Backup gespeichert in backup/configs_$stamp.tar.gz"
}

show_menu() {
  echo -e "\n🌐 ${GREEN}Sprachassistent Setup CLI${RESET}"
  echo "1) Konfiguration ersetzen (template_config.sh)"
  echo "2) Verbindungen testen (verify_all_nodes.sh)"
  echo "3) Alle Nodes installieren (install_all_nodes.sh)"
  echo "4) Nur Raspi 4 installieren"
  echo "5) Nur Raspi 400 installieren"
  echo "6) Nur Odroid (Docker) installieren"
  echo "7) WebSocket-Server lokal installieren"
  echo "8) Desktop-App bauen"
  echo "9) Flowise/n8n via NPM lokal installieren"
  echo "10) Logs anzeigen (journalctl)"
  echo "11) Dienste neu starten"
  echo "12) .env prüfen"
  echo "13) .env interaktiv erstellen"
  echo "14) Backup/Export Configs & Logs"
  echo "15) Beenden"
  echo -n "> Auswahl: "
}

while true; do
  show_menu
  read -r choice
  case $choice in
    1) bash "$SCRIPTS/template_config.sh" && log "Konfiguration aktualisiert." ;;
    2) bash "$SCRIPTS/verify_all_nodes.sh" && log "Verbindungsprüfung abgeschlossen." ;;
    3) bash "$SCRIPTS/install_all_nodes.sh" && log "Alle Nodes installiert." ;;
    4) bash "$SCRIPTS/raspi4/install-raspi4.sh" && log "Raspi 4 fertig." ;;
    5) bash "$SCRIPTS/raspi400/install-raspi400.sh" && log "Raspi 400 fertig." ;;
    6) bash "$SCRIPTS/odroid/install-odroid.sh" && log "Odroid (Docker) fertig." ;;
    7) bash "$SCRIPTS/ws-server/install.sh" && log "WebSocket-Server installiert." ;;
    8) bash "$APPS/build_all.sh" && log "Desktop-App(s) gebaut." ;;
    9)
      echo "📦 Installiere Flowise & n8n via NPM..."
      sudo apt update && sudo apt install -y nodejs npm
      sudo npm install -g n8n flowise
      nohup npx flowise start > flowise.log 2>&1 &
      log "Flowise gestartet unter http://localhost:3000"
      echo "ℹ️  Starte n8n manuell mit: n8n"
      ;;
    10) sudo journalctl -u ws-server.service -n 50 --no-pager ;;
    11) restart_services ;;
    12) validate_env ;;
    13) interactive_env_fill ;;
    14) backup_configs ;;
    15) echo "Bye!" && exit 0 ;;
    *) warn "Ungültige Auswahl." ;;
  esac
done
