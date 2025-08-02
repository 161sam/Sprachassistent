#!/usr/bin/env bash
set -e

# 🔄 Lädt Variablen aus .env und ersetzt Platzhalter in config/*.json

if [ ! -f .env ]; then
  echo "❌ .env Datei nicht gefunden!"
  exit 1
fi

# === ERWARTETE VARIABLEN ===
REQUIRED_VARS=(
  WS_TOKEN RASPI4_HOST RASPI400_HOST ODROID_HOST
  FLOWISE_URL FLOWISE_API_KEY N8N_HOST N8N_PORT
  WHISPER_MODEL_SIZE WHISPER_DEVICE WHISPER_LANG
  PIPER_MODEL PIPER_MODEL_DIR KOKORO_MODEL
)

# === LADEN ===
export $(grep -v '^#' .env | xargs)

# === PRÜFEN ===
missing=0
for var in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!var}" ]; then
    echo "❗ FEHLT: $var"
    missing=1
  fi
done

if [ $missing -eq 1 ]; then
  echo "⛔ Fehlende Variablen in .env. Abbruch."
  exit 1
fi

# === ERSETZUNG ===
replace_vars() {
  local input=$1
  local output=$2
  echo "🔧 Ersetze Variablen in $input → $output"
  envsubst < "$input" > "$output"
}

# config/raspi400
replace_vars config/raspi400/gui-settings.json config/raspi400/gui-settings.json

# config/raspi4
replace_vars config/raspi4/stt-config.json config/raspi4/stt-config.json
replace_vars config/raspi4/tts-config.json config/raspi4/tts-config.json

# config/odroid
replace_vars config/odroid/flowise-settings.json config/odroid/flowise-settings.json

echo "✅ Alle Konfigurationsdateien aktualisiert."
