#!/bin/bash

# Voice Assistant Apps - Cross-Platform Build Script
# Erstellt Desktop (Electron) und Mobile (Cordova) Apps

set -e  # Script bei Fehlern beenden

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funktionen
print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE} Voice Assistant Build Script${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️ $1${NC}"
}

check_requirements() {
    print_info "Überprüfe Systemanforderungen..."
    
    # Node.js
    if ! command -v node &> /dev/null; then
        print_error "Node.js ist nicht installiert"
        exit 1
    fi
    print_success "Node.js: $(node --version)"
    
    # NPM
    if ! command -v npm &> /dev/null; then
        print_error "NPM ist nicht installiert"
        exit 1
    fi
    print_success "NPM: $(npm --version)"
    
    # Git
    if ! command -v git &> /dev/null; then
        print_warning "Git ist nicht installiert - Versionsinformationen werden nicht verfügbar sein"
    else
        print_success "Git: $(git --version)"
    fi
}

setup_directories() {
    print_info "Erstelle Projektstruktur..."
    
    # Hauptverzeichnisse
    mkdir -p desktop/src
    mkdir -p desktop/assets
    mkdir -p desktop/build
    mkdir -p mobile/www/js
    mkdir -p mobile/www/css
    mkdir -p mobile/www/assets
    mkdir -p mobile/hooks
    mkdir -p shared
    mkdir -p dist
    
    print_success "Projektstruktur erstellt"
}

copy_shared_files() {
    print_info "Kopiere gemeinsame Dateien..."
    
    # Shared files zu Desktop kopieren
    if [ -f "shared/app.js" ]; then
        cp shared/app.js desktop/src/
        print_success "app.js zu Desktop kopiert"
    fi
    
    # Shared files zu Mobile kopieren
    if [ -f "shared/app.js" ]; then
        cp shared/app.js mobile/www/js/
        print_success "app.js zu Mobile kopiert"
    fi
    
    # Assets kopieren falls vorhanden
    if [ -d "shared/assets" ]; then
        cp -r shared/assets/* desktop/assets/ 2>/dev/null || true
        cp -r shared/assets/* mobile/www/assets/ 2>/dev/null || true
        print_success "Assets kopiert"
    fi
}

build_desktop() {
    print_info "Baue Desktop App (Electron)..."
    
    if [ ! -d "desktop" ]; then
        print_error "Desktop-Verzeichnis nicht gefunden"
        return 1
    fi
    
    cd desktop
    
    # Dependencies installieren falls nicht vorhanden
    if [ ! -d "node_modules" ]; then
        print_info "Installiere Desktop Dependencies..."
        npm install
    fi
    
    # Build-Platform bestimmen
    BUILD_PLATFORM=${1:-"current"}
    
    case $BUILD_PLATFORM in
        "all")
            print_info "Baue für alle Platformen..."
            npm run build-all
            ;;
        "windows"|"win")
            print_info "Baue für Windows..."
            npm run build-win
            ;;
        "mac"|"darwin")
            print_info "Baue für macOS..."
            npm run build-mac
            ;;
        "linux")
            print_info "Baue für Linux..."
            npm run build-linux
            ;;
        *)
            print_info "Baue für aktuelle Plattform..."
            npm run build
            ;;
    esac
    
    if [ $? -eq 0 ]; then
        print_success "Desktop App erfolgreich gebaut"
        
        # Build-Ergebnisse anzeigen
        if [ -d "dist" ]; then
            print_info "Build-Ergebnisse in desktop/dist/:"
            ls -la dist/
        fi
    else
        print_error "Desktop Build fehlgeschlagen"
        cd ..
        return 1
    fi
    
    cd ..
}

build_mobile() {
    print_info "Baue Mobile App (Cordova)..."
    
    if [ ! -d "mobile" ]; then
        print_error "Mobile-Verzeichnis nicht gefunden"
        return 1
    fi
    
    cd mobile
    
    # Cordova global installieren falls nicht vorhanden
    if ! command -v cordova &> /dev/null; then
        print_info "Installiere Cordova global..."
        npm install -g cordova
    fi
    
    # Android SDK prüfen
    if [ -z "$ANDROID_HOME" ]; then
        print_warning "ANDROID_HOME nicht gesetzt - Android Build könnte fehlschlagen"
        print_info "Bitte Android Studio installieren und ANDROID_HOME setzen"
    else
        print_success "Android SDK gefunden: $ANDROID_HOME"
    fi
    
    # Cordova Dependencies installieren
    if [ ! -d "node_modules" ]; then
        print_info "Installiere Mobile Dependencies..."
        npm install
    fi
    
    # Platform hinzufügen falls nicht vorhanden
    if [ ! -d "platforms/android" ]; then
        print_info "Füge Android Platform hinzu..."
        cordova platform add android
    fi
    
    # Plugins installieren
    print_info "Installiere Cordova Plugins..."
    cordova prepare android
    
    # Build-Typ bestimmen
    BUILD_TYPE=${2:-"debug"}
    
    if [ "$BUILD_TYPE" == "release" ]; then
        print_info "Baue Release APK..."
        cordova build android --release
        
        if [ $? -eq 0 ]; then
            print_success "Release APK erfolgreich gebaut"
            print_warning "APK muss noch signiert werden für Store-Upload"
            
            # APK-Pfad anzeigen
            APK_PATH="platforms/android/app/build/outputs/apk/release/"
            if [ -d "$APK_PATH" ]; then
                print_info "APK-Dateien in $APK_PATH:"
                ls -la "$APK_PATH"
            fi
        else
            print_error "Release Build fehlgeschlagen"
            cd ..
            return 1
        fi
    else
        print_info "Baue Debug APK..."
        cordova build android --debug
        
        if [ $? -eq 0 ]; then
            print_success "Debug APK erfolgreich gebaut"
            
            # APK-Pfad anzeigen
            APK_PATH="platforms/android/app/build/outputs/apk/debug/"
            if [ -d "$APK_PATH" ]; then
                print_info "APK-Dateien in $APK_PATH:"
                ls -la "$APK_PATH"
            fi
        else
            print_error "Debug Build fehlgeschlagen"
            cd ..
            return 1
        fi
    fi
    
    cd ..
}

create_distribution() {
    print_info "Erstelle Distribution-Paket..."
    
    # Dist-Verzeichnis bereinigen
    rm -rf dist/*
    
    # Desktop Builds kopieren
    if [ -d "desktop/dist" ]; then
        mkdir -p dist/desktop
        cp -r desktop/dist/* dist/desktop/
        print_success "Desktop Builds zu dist/ kopiert"
    fi
    
    # Mobile Builds kopieren
    if [ -d "mobile/platforms/android/app/build/outputs/apk" ]; then
        mkdir -p dist/mobile/android
        find mobile/platforms/android/app/build/outputs/apk -name "*.apk" -exec cp {} dist/mobile/android/ \;
        print_success "Android APKs zu dist/ kopiert"
    fi
    
    # Build-Info erstellen
    create_build_info
    
    print_success "Distribution-Paket erstellt in: dist/"
}

create_build_info() {
    print_info "Erstelle Build-Informationen..."
    
    BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    BUILD_VERSION="2.1.0"
    
    # Git-Informationen sammeln
    if command -v git &> /dev/null && [ -d ".git" ]; then
        GIT_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
        GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
        GIT_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "unknown")
    else
        GIT_COMMIT="unknown"
        GIT_BRANCH="unknown"
        GIT_TAG="unknown"
    fi
    
    # System-Informationen
    BUILD_OS=$(uname -s)
    BUILD_ARCH=$(uname -m)
    NODE_VERSION=$(node --version)
    NPM_VERSION=$(npm --version)
    
    # Build-Info JSON erstellen
    cat > dist/build-info.json << EOF
{
  "version": "$BUILD_VERSION",
  "buildDate": "$BUILD_DATE",
  "git": {
    "commit": "$GIT_COMMIT",
    "branch": "$GIT_BRANCH",
    "tag": "$GIT_TAG"
  },
  "system": {
    "os": "$BUILD_OS",
    "arch": "$BUILD_ARCH",
    "nodeVersion": "$NODE_VERSION",
    "npmVersion": "$NPM_VERSION"
  },
  "platforms": {
    "desktop": $([ -d "dist/desktop" ] && echo "true" || echo "false"),
    "mobile": $([ -d "dist/mobile" ] && echo "true" || echo "false")
  }
}
EOF
    
    print_success "Build-Info erstellt: dist/build-info.json"
}

show_summary() {
    print_header
    echo -e "${GREEN}🎉 Build erfolgreich abgeschlossen!${NC}"
    echo ""
    
    if [ -d "dist/desktop" ]; then
        echo -e "${BLUE}🖥️ Desktop Apps:${NC}"
        find dist/desktop -name "*.exe" -o -name "*.dmg" -o -name "*.AppImage" -o -name "*.deb" | while read file; do
            SIZE=$(du -h "$file" | cut -f1)
            echo -e "   📦 $(basename "$file") (${SIZE})"
        done
        echo ""
    fi
    
    if [ -d "dist/mobile" ]; then
        echo -e "${BLUE}📱 Mobile Apps:${NC}"
        find dist/mobile -name "*.apk" -o -name "*.aab" | while read file; do
            SIZE=$(du -h "$file" | cut -f1)
            echo -e "   📦 $(basename "$file") (${SIZE})"
        done
        echo ""
    fi
    
    if [ -f "dist/build-info.json" ]; then
        echo -e "${BLUE}ℹ️ Build-Informationen:${NC}"
        echo -e "   📅 $(cat dist/build-info.json | grep -o '"buildDate":"[^"]*"' | cut -d'"' -f4)"
        echo -e "   🌿 Branch: $(cat dist/build-info.json | grep -o '"branch":"[^"]*"' | cut -d'"' -f4)"
        echo -e "   📝 Commit: $(cat dist/build-info.json | grep -o '"commit":"[^"]*"' | cut -d'"' -f4 | cut -c1-8)"
        echo ""
    fi
    
    echo -e "${GREEN}✨ Bereit für Distribution!${NC}"
}

show_help() {
    echo "Voice Assistant Build Script"
    echo ""
    echo "Usage: $0 [desktop|mobile|all] [debug|release]"
    echo ""
    echo "Optionen:"
    echo "  desktop        Nur Desktop App bauen"
    echo "  mobile         Nur Mobile App bauen"
    echo "  all            Beide Apps bauen (Standard)"
    echo ""
    echo "Build-Typ (nur für Mobile):"
    echo "  debug          Debug Build (Standard)"
    echo "  release        Release Build (Production)"
    echo ""
    echo "Desktop Platform (nur für Desktop):"
    echo "  current        Aktuelle Plattform (Standard)"
    echo "  windows        Windows Build"
    echo "  mac            macOS Build"
    echo "  linux          Linux Build"
    echo "  all            Alle Platformen"
    echo ""
    echo "Beispiele:"
    echo "  $0                    # Beide Apps, Debug"
    echo "  $0 desktop            # Nur Desktop"
    echo "  $0 mobile release     # Nur Mobile, Release"
    echo "  $0 all release        # Beide Apps, Release"
}

# Hauptlogik
main() {
    if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
        show_help
        exit 0
    fi
    
    print_header
    
    # Systemanforderungen prüfen
    check_requirements
    
    # Projektstruktur erstellen
    setup_directories
    
    # Shared Files kopieren
    copy_shared_files
    
    # Build-Ziel bestimmen
    BUILD_TARGET=${1:-"all"}
    BUILD_TYPE=${2:-"debug"}
    
    case $BUILD_TARGET in
        "desktop")
            build_desktop "$BUILD_TYPE"
            ;;
        "mobile")
            build_mobile "$BUILD_TARGET" "$BUILD_TYPE"
            ;;
        "all")
            print_info "Baue beide Apps..."
            build_desktop "$BUILD_TYPE"
            build_mobile "$BUILD_TARGET" "$BUILD_TYPE"
            ;;
        *)
            print_error "Unbekanntes Build-Ziel: $BUILD_TARGET"
            show_help
            exit 1
            ;;
    esac
    
    # Distribution erstellen
    create_distribution
    
    # Zusammenfassung anzeigen
    show_summary
}

# Script ausführen
main "$@"
