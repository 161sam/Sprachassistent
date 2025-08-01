#!/usr/bin/env bash
set -e

# 🔄 Lädt Variablen aus .env und ersetzt Platzhalter in config/*.json

if [ ! -f .env ]; then
  echo "❌ .env Datei nicht gefunden!"
  exit 1
fi

export $(grep -v '^#' .env | xargs)

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
