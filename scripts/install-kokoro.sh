#!/bin/bash
"""
Installation von Kokoro TTS für den Sprachassistenten
Lädt Modell-Dateien herunter und konfiguriert das System
"""

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
[ -f "$SCRIPT_DIR/../.env.kokoro" ] && source "$SCRIPT_DIR/../.env.kokoro"

echo "🎤 Kokoro TTS Installation"
echo "=========================="
echo

# Konfiguration
KOKORO_DIR="${KOKORO_MODEL_DIR:-$HOME/.local/share/kokoro}"
MODEL_FILE="${KOKORO_MODEL:-kokoro-v1.0.int8.onnx}"
VOICES_FILE="${KOKORO_VOICES_FILE:-voices-v1.0.bin}"
MODEL_URL="${KOKORO_MODEL_URL:-https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.int8.onnx}"
VOICES_URL="${KOKORO_VOICES_URL:-https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin}"
KOKORO_LANG="${KOKORO_LANG:-en-us}"

# Funktionen
log_info() {
    echo "ℹ️  $1"
}

log_success() {
    echo "✅ $1"
}

log_error() {
    echo "❌ $1"
}

log_warning() {
    echo "⚠️  $1"
}

check_dependencies() {
    log_info "Prüfe Abhängigkeiten..."
    
    # Python 3.8+
    if ! python3 -c "import sys; assert sys.version_info >= (3, 8)" 2>/dev/null; then
        log_error "Python 3.8+ erforderlich"
        exit 1
    fi
    log_success "Python Version OK"
    
    # pip
    if ! command -v pip3 &> /dev/null; then
        log_error "pip3 nicht gefunden"
        exit 1
    fi
    log_success "pip3 verfügbar"
    
    # wget oder curl
    if command -v wget &> /dev/null; then
        DOWNLOAD_CMD="wget -O"
    elif command -v curl &> /dev/null; then
        DOWNLOAD_CMD="curl -L -o"
    else
        log_error "wget oder curl erforderlich für Download"
        exit 1
    fi
    log_success "Download-Tool verfügbar"
}

install_python_packages() {
    log_info "Installiere Python-Pakete..."
    
    # Virtual Environment erstellen falls noch nicht vorhanden
    if [ ! -d "venv" ]; then
        log_info "Erstelle Virtual Environment..."
        python3 -m venv venv
    fi
    
    # Virtual Environment aktivieren
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Kokoro TTS installieren
    log_info "Installiere kokoro-onnx..."
    pip install kokoro-onnx
    
    # SoundFile für Audio-Verarbeitung
    log_info "Installiere soundfile..."
    pip install soundfile
    
    # Weitere Abhängigkeiten
    log_info "Installiere weitere Abhängigkeiten..."
    pip install aiohttp aiofiles numpy
    
    log_success "Python-Pakete erfolgreich installiert"
}

create_directories() {
    log_info "Erstelle Verzeichnisse..."
    
    # Kokoro-Verzeichnis erstellen
    mkdir -p "$KOKORO_DIR"
    log_success "Kokoro-Verzeichnis erstellt: $KOKORO_DIR"
    
    # Backup-Verzeichnis für alte Modelle
    mkdir -p "$KOKORO_DIR/backup"
    
    # Logs-Verzeichnis
    mkdir -p "$KOKORO_DIR/logs"
}

download_models() {
    log_info "Lade Kokoro-Modelle herunter..."
    
    # Modell-Datei prüfen/herunterladen
    MODEL_PATH="$KOKORO_DIR/$MODEL_FILE"
    if [ -f "$MODEL_PATH" ]; then
        log_warning "Modell-Datei existiert bereits: $MODEL_PATH"
        read -p "Erneut herunterladen? (y/N): " -r
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            mv "$MODEL_PATH" "$KOKORO_DIR/backup/${MODEL_FILE}.$(date +%Y%m%d_%H%M%S)"
        else
            log_info "Verwende existierende Modell-Datei"
            return
        fi
    fi
    
    log_info "Lade Modell herunter: $MODEL_FILE"
    if $DOWNLOAD_CMD "$MODEL_PATH" "$MODEL_URL"; then
        log_success "Modell heruntergeladen: $(du -h "$MODEL_PATH" | cut -f1)"
    else
        log_error "Download der Modell-Datei fehlgeschlagen"
        exit 1
    fi
    
    # Voices-Datei herunterladen
    VOICES_PATH="$KOKORO_DIR/$VOICES_FILE"
    if [ -f "$VOICES_PATH" ]; then
        log_warning "Voices-Datei existiert bereits: $VOICES_PATH"
        mv "$VOICES_PATH" "$KOKORO_DIR/backup/${VOICES_FILE}.$(date +%Y%m%d_%H%M%S)"
    fi
    
    log_info "Lade Voices herunter: $VOICES_FILE"
    if $DOWNLOAD_CMD "$VOICES_PATH" "$VOICES_URL"; then
        log_success "Voices heruntergeladen: $(du -h "$VOICES_PATH" | cut -f1)"
    else
        log_error "Download der Voices-Datei fehlgeschlagen"
        exit 1
    fi
}

verify_installation() {
    log_info "Verifiziere Installation..."
    
    # Modell-Dateien prüfen
    MODEL_PATH="$KOKORO_DIR/$MODEL_FILE"
    VOICES_PATH="$KOKORO_DIR/$VOICES_FILE"
    
    if [ ! -f "$MODEL_PATH" ]; then
        log_error "Modell-Datei nicht gefunden: $MODEL_PATH"
        exit 1
    fi
    
    if [ ! -f "$VOICES_PATH" ]; then
        log_error "Voices-Datei nicht gefunden: $VOICES_PATH"
        exit 1
    fi
    
    # Dateigröße prüfen (grobe Validierung)
    MODEL_SIZE=$(stat -f%z "$MODEL_PATH" 2>/dev/null || stat -c%s "$MODEL_PATH" 2>/dev/null)
    if [ "$MODEL_SIZE" -lt 70000000 ]; then  # < 70MB
        log_error "Modell-Datei scheint unvollständig zu sein (Größe: $MODEL_SIZE Bytes)"
        exit 1
    fi
    
    log_success "Dateien erfolgreich verifiziert"
    log_info "  Modell: $(ls -lh "$MODEL_PATH" | awk '{print $5}')"
    log_info "  Voices: $(ls -lh "$VOICES_PATH" | awk '{print $5}')"
}

test_kokoro() {
    log_info "Teste Kokoro TTS..."
    
    # Virtual Environment aktivieren
    source venv/bin/activate
    
    # Test-Script erstellen
    cat > kokoro_test.py << 'EOF'
#!/usr/bin/env python3
import sys
import os
import tempfile

try:
    from kokoro_onnx import Kokoro
    import soundfile as sf
    
    # Modell-Pfade
    model_path = os.path.expanduser("~/.local/share/kokoro/kokoro-v1.0.int8.onnx")
    voices_path = os.path.expanduser("~/.local/share/kokoro/voices-v1.0.bin")
    
    if not os.path.exists(model_path):
        print(f"❌ Modell nicht gefunden: {model_path}")
        sys.exit(1)
        
    if not os.path.exists(voices_path):
        print(f"❌ Voices nicht gefunden: {voices_path}")
        sys.exit(1)
    
    # Kokoro initialisieren
    print("🎤 Initialisiere Kokoro TTS...")
    kokoro = Kokoro(model_path, voices_path)
    
    # Test-Synthese
    test_text = "Hello world, this is a test of Kokoro TTS."
    print(f"🔊 Teste: '{test_text}'")
    
    samples, sample_rate = kokoro.create(
        text=test_text,
        voice="af_sarah",
        speed=1.0,
        lang="$KOKORO_LANG"
    )
    
    # Test-Audio speichern
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        test_file = f.name
        
    sf.write(test_file, samples, sample_rate)
    
    # Verifikation
    file_size = os.path.getsize(test_file)
    if file_size > 1000:  # > 1KB
        print(f"✅ Test erfolgreich! Audio erstellt: {file_size} Bytes")
        print(f"📁 Test-Datei: {test_file}")
        print("🎵 Hören Sie die Datei ab um die Qualität zu prüfen.")
    else:
        print(f"❌ Test fehlgeschlagen - Audio zu klein: {file_size} Bytes")
        sys.exit(1)
        
except ImportError as e:
    print(f"❌ Import-Fehler: {e}")
    print("Stellen Sie sicher, dass kokoro-onnx installiert ist")
    sys.exit(1)
except Exception as e:
    print(f"❌ Test fehlgeschlagen: {e}")
    sys.exit(1)
EOF

    # Test ausführen
    if python3 kokoro_test.py; then
        log_success "Kokoro TTS Test erfolgreich"
        rm kokoro_test.py
    else
        log_error "Kokoro TTS Test fehlgeschlagen"
        rm -f kokoro_test.py
        exit 1
    fi
}

create_config() {
    log_info "Erstelle Konfiguration..."
    
    # Konfigurationsdatei erstellen
    cat > "$KOKORO_DIR/config.json" << EOF
{
    "model_path": "$KOKORO_DIR/$MODEL_FILE",
    "voices_path": "$KOKORO_DIR/$VOICES_FILE",
    "default_voice": "af_sarah",
    "default_speed": 1.0,
    "default_language": "$KOKORO_LANG",
    "cache_enabled": true,
    "cache_size_mb": 100,
    "installation_date": "$(date -Iseconds)",
    "version": "1.0"
}
EOF

    log_success "Konfiguration erstellt: $KOKORO_DIR/config.json"
}

show_summary() {
    echo
    echo "🎉 Kokoro TTS Installation abgeschlossen!"
    echo "========================================"
    echo
    echo "📂 Installation-Verzeichnis: $KOKORO_DIR"
    echo "📄 Modell-Datei: $MODEL_FILE ($(du -h "$KOKORO_DIR/$MODEL_FILE" | cut -f1))"
    echo "🎵 Voices-Datei: $VOICES_FILE ($(du -h "$KOKORO_DIR/$VOICES_FILE" | cut -f1))"
    echo
    echo "🔧 Verwendung:"
    echo "   - Der Sprachassistent kann nun Kokoro TTS verwenden"
    echo "   - Wechseln Sie im WebSocket mit: {\"type\": \"switch_tts_engine\", \"engine\": \"kokoro\"}"
    echo "   - Verfügbare Stimmen: af_sarah, af_heart, af_sky, af_nova, af_alloy, ..."
    echo
    echo "📝 Nächste Schritte:"
    echo "   1. Starten Sie den Sprachassistenten neu"
    echo "   2. Testen Sie das Engine-Switching in der GUI"
    echo "   3. Vergleichen Sie die Audio-Qualität zwischen Piper und Kokoro"
    echo
    echo "🆘 Support:"
    echo "   - Logs: $KOKORO_DIR/logs/"
    echo "   - Konfiguration: $KOKORO_DIR/config.json" 
    echo "   - Test-Script: backend/test_tts_system.py"
    echo
}

# Hauptfunktion
main() {
    echo "Installiere Kokoro TTS für den Sprachassistenten..."
    echo
    
    check_dependencies
    create_directories
    install_python_packages
    download_models
    verify_installation
    test_kokoro
    create_config
    show_summary
    
    log_success "Installation erfolgreich abgeschlossen!"
}

# Script ausführen
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
