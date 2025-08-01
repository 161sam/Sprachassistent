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

show_menu() {
  echo -e "\n🌐 ${GREEN}Sprachassistent Setup CLI${RESET}"
  echo "1) Konfiguration ersetzen (template_config.sh)"
  echo "2) Verbindungen testen (verify_all_nodes.sh)"
  echo "3) Alle Nodes installieren (install_all_nodes.sh)"
  echo "4) Nur Raspi 4 installieren"
  echo "5) Nur Raspi 400 installieren"
  echo "6) Nur Odroid installieren"
  echo "7) WebSocket-Server lokal installieren"
  echo "8) Desktop-App bauen"
  echo "9) Beenden"
  echo -n "> Auswahl: "
}

while true; do
  show_menu
  read -r choice
  case $choice in
    1)
      bash "$SCRIPTS/template_config.sh" && log "Konfiguration aktualisiert."
      ;;
    2)
      bash "$SCRIPTS/verify_all_nodes.sh" && log "Verbindungsprüfung abgeschlossen."
      ;;
    3)
      bash "$SCRIPTS/install_all_nodes.sh" && log "Alle Nodes installiert."
      ;;
    4)
      bash "$SCRIPTS/raspi4/install-raspi4.sh" && log "Raspi 4 fertig."
      ;;
    5)
      bash "$SCRIPTS/raspi400/install-raspi400.sh" && log "Raspi 400 fertig."
      ;;
    6)
      bash "$SCRIPTS/odroid/install-odroid.sh" && log "Odroid fertig."
      ;;
    7)
      bash "$SCRIPTS/ws-server/install.sh" && log "WebSocket-Server installiert."
      ;;
    8)
      bash "$APPS/build_all.sh" && log "Desktop-App(s) gebaut."
      ;;
    9)
      echo "Bye!" && exit 0
      ;;
    *)
      warn "Ungültige Auswahl."
      ;;
  esac

done
