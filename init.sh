#!/bin/bash

# voice-assistant-raspi Projektstruktur Setup Script
# Erstellt alle notwendigen Verzeichnisse und Dateien für das Sprachassistenten-Projekt

set -e  # Script bei Fehlern beenden

echo "🚀 Initialisiere voice-assistant-raspi Projektstruktur..."

# Verzeichnisse erstellen
echo "📁 Erstelle Verzeichnisse..."
mkdir -p config/raspi4
mkdir -p config/raspi400  
mkdir -p config/odroid
mkdir -p scripts
mkdir -p gui
mkdir -p docs
mkdir -p test

echo "✅ Verzeichnisse erstellt"

# Root-Level Dateien erstellen (außer README.md)
echo "📄 Erstelle Root-Level Dateien..."

# .gitignore
if [ ! -f .gitignore ]; then
    touch .gitignore
    echo "   ✓ .gitignore erstellt"
else
    echo "   ⚠ .gitignore existiert bereits"
fi

# docker-compose.yml
if [ ! -f docker-compose.yml ]; then
    touch docker-compose.yml
    echo "   ✓ docker-compose.yml erstellt"
else
    echo "   ⚠ docker-compose.yml existiert bereits"
fi

# env.example
if [ ! -f env.example ]; then
    touch env.example
    echo "   ✓ env.example erstellt"
else
    echo "   ⚠ env.example existiert bereits"
fi

# flowise-config.json
if [ ! -f flowise-config.json ]; then
    touch flowise-config.json
    echo "   ✓ flowise-config.json erstellt"
else
    echo "   ⚠ flowise-config.json existiert bereits"
fi

# Config-Dateien erstellen
echo "⚙️ Erstelle Konfigurationsdateien..."

# raspi4 config
if [ ! -f config/raspi4/stt-config.json ]; then
    touch config/raspi4/stt-config.json
    echo "   ✓ config/raspi4/stt-config.json erstellt"
fi

if [ ! -f config/raspi4/tts-config.json ]; then
    touch config/raspi4/tts-config.json
    echo "   ✓ config/raspi4/tts-config.json erstellt"
fi

# raspi400 config
if [ ! -f config/raspi400/gui-settings.json ]; then
    touch config/raspi400/gui-settings.json
    echo "   ✓ config/raspi400/gui-settings.json erstellt"
fi

# odroid config
if [ ! -f config/odroid/flowise-settings.json ]; then
    touch config/odroid/flowise-settings.json
    echo "   ✓ config/odroid/flowise-settings.json erstellt"
fi

# Script-Dateien erstellen
echo "🔧 Erstelle Shell-Skripte..."

scripts_list=(
    "setup-tailscale.sh"
    "start-stt.sh"
    "start-tts.sh"
    "install-piper.sh"
)

for script in "${scripts_list[@]}"; do
    if [ ! -f "scripts/$script" ]; then
        touch "scripts/$script"
        chmod +x "scripts/$script"
        echo "   ✓ scripts/$script erstellt (ausführbar)"
    else
        echo "   ⚠ scripts/$script existiert bereits"
    fi
done

# GUI-Dateien erstellen
echo "🖥️ Erstelle GUI-Dateien..."

gui_files=(
    "index.html"
    "app.js"
    "styles.css"
)

for file in "${gui_files[@]}"; do
    if [ ! -f "gui/$file" ]; then
        touch "gui/$file"
        echo "   ✓ gui/$file erstellt"
    else
        echo "   ⚠ gui/$file existiert bereits"
    fi
done

# Dokumentationsdateien erstellen
echo "📚 Erstelle Dokumentationsdateien..."

docs_list=(
    "architecture.md"
    "routing.md"
    "tailscale-setup.md"
    "skill-system.md"
)

for doc in "${docs_list[@]}"; do
    if [ ! -f "docs/$doc" ]; then
        touch "docs/$doc"
        echo "   ✓ docs/$doc erstellt"
    else
        echo "   ⚠ docs/$doc existiert bereits"
    fi
done

# Test-Dateien erstellen
echo "🧪 Erstelle Test-Dateien..."

if [ ! -f test/example-audio.wav ]; then
    touch test/example-audio.wav
    echo "   ✓ test/example-audio.wav erstellt"
else
    echo "   ⚠ test/example-audio.wav existiert bereits"
fi

# Abschlussmeldung
echo ""
echo "🎉 Projektstruktur erfolgreich initialisiert!"
echo ""
echo "📋 Erstellte Struktur:"
echo "├── .gitignore"
echo "├── docker-compose.yml"
echo "├── env.example"
echo "├── flowise-config.json"
echo "├── config/"
echo "│   ├── raspi4/ (stt-config.json, tts-config.json)"
echo "│   ├── raspi400/ (gui-settings.json)"
echo "│   └── odroid/ (flowise-settings.json)"
echo "├── scripts/ (setup-tailscale.sh, start-stt.sh, start-tts.sh, install-piper.sh)"
echo "├── gui/ (index.html, app.js, styles.css)"
echo "├── docs/ (architecture.md, routing.md, tailscale-setup.md, skill-system.md)"
echo "└── test/ (example-audio.wav)"
echo ""
echo "💡 Nächste Schritte:"
echo "   1. Bearbeite env.example mit deinen Konfigurationswerten"
echo "   2. Kopiere env.example zu .env"
echo "   3. Fülle die Konfigurationsdateien in config/ aus"
echo "   4. Implementiere die Shell-Skripte in scripts/"
echo ""
echo "ℹ️ README.md wurde nicht verändert (existiert bereits)"
