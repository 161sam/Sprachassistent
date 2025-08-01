# 🚀 Build-Anleitung: KI-Sprachassistent

Entwicklungs- und Deployment-Guide für Desktop (Electron) und Mobile (Android/Cordova) Versionen.

## 📁 Projektstruktur

```
voice-assistant-apps/
├── shared/                     # Gemeinsame Dateien
│   ├── index.html             # Hauptseite (von vorheriger GUI)
│   ├── styles.css             # CSS Styles
│   ├── app.js                 # Haupt-JavaScript
│   └── assets/               # Icons, Bilder, etc.
├── desktop/                   # Electron Desktop App
│   ├── package.json
│   ├── src/
│   │   ├── main.js           # Electron Hauptprozess
│   │   ├── preload.js        # Preload Script
│   │   └── index.html        # Desktop HTML (Link zu shared/)
│   ├── assets/               # Desktop-spezifische Assets
│   └── build/                # Build-Output
├── mobile/                    # Cordova Mobile App  
│   ├── config.xml            # Cordova Konfiguration
│   ├── www/                  # Web-Assets (Link zu shared/)
│   ├── platforms/            # Platform-spezifische Builds
│   ├── plugins/              # Cordova Plugins
│   └── hooks/                # Build-Hooks
└── docs/                     # Dokumentation
```

---

## 🖥️ Desktop App (Electron)

### Voraussetzungen
```bash
# Node.js (Version 18+)
node --version
npm --version

# Git
git --version
```

### Installation & Setup
```bash
# Projekt-Ordner erstellen
mkdir voice-assistant-apps
cd voice-assistant-apps

# Desktop-Ordner erstellen
mkdir desktop
cd desktop

# Package.json erstellen (vom Artifact)
# main.js erstellen (vom Artifact)  
# preload.js erstellen (vom Artifact)

# Dependencies installieren
npm install
```

### Entwicklung
```bash
# Development-Modus starten
npm run dev

# Oder standard start
npm start
```

### Build & Distribution
```bash
# Für aktuelles System builden
npm run build

# Platform-spezifisch builden
npm run build-win    # Windows
npm run build-mac    # macOS  
npm run build-linux  # Linux

# Alle Platformen (benötigt entsprechende Umgebung)
npm run dist
```

### Desktop-spezifische Features
- **Native Menüs** (Datei, Bearbeiten, Ansicht, etc.)
- **System Tray Integration**
- **Auto-Updater** 
- **Keyboard Shortcuts**
- **Native Benachrichtigungen**
- **Fenster-Management**

---

## 📱 Mobile App (Android/Cordova)

### Voraussetzungen
```bash
# Node.js & NPM
node --version
npm --version

# Cordova CLI global installieren
npm install -g cordova

# Android SDK (Android Studio empfohlen)
# Java JDK 11+
# Gradle
```

### Android SDK Setup
```bash
# Android Studio installieren
# SDK Tools installieren:
# - Android SDK Build-Tools
# - Android SDK Platform-Tools  
# - Android SDK Tools
# - Google USB Driver (Windows)

# Umgebungsvariablen setzen
export ANDROID_HOME=$HOME/Android/Sdk
export PATH=$PATH:$ANDROID_HOME/tools
export PATH=$PATH:$ANDROID_HOME/platform-tools
export PATH=$PATH:$ANDROID_HOME/build-tools/34.0.0
```

### Cordova Projekt Setup
```bash
# Cordova Projekt erstellen
cordova create mobile com.voiceassistant.mobile "KI-Sprachassistent"
cd mobile

# Android Platform hinzufügen
cordova platform add android

# Config.xml überschreiben (vom Artifact)
# mobile.js zu www/js/ hinzufügen

# Plugins installieren (werden automatisch aus config.xml installiert)
cordova prepare android
```

### Entwicklung & Testing
```bash
# Auf Gerät/Emulator testen
cordova run android

# Debug-Build
cordova build android --debug

# Live-Reload für Entwicklung
cordova run android --livereload
```

### Production Build
```bash
# Release-Build erstellen
cordova build android --release

# APK signieren (benötigt Keystore)
# 1. Keystore erstellen:
keytool -genkey -v -keystore voice-assistant.keystore -alias voice-assistant -keyalg RSA -keysize 2048 -validity 10000

# 2. APK signieren:
jarsigner -verbose -sigalg SHA1withRSA -digestalg SHA1 -keystore voice-assistant.keystore platforms/android/app/build/outputs/apk/release/app-release-unsigned.apk voice-assistant

# 3. Zipalign:
zipalign -v 4 platforms/android/app/build/outputs/apk/release/app-release-unsigned.apk KI-Sprachassistent.apk
```

### Mobile-spezifische Features
- **Sprach-Plugins** (Speech Recognition, TTS)
- **Background-Mode** für kontinuierliche Nutzung
- **Haptic Feedback** (Vibrationen)
- **Push-Benachrichtigungen**
- **Berechtigungsmanagement**
- **Touch-Optimierungen**
- **Network-Status-Monitoring**

---

## 🔧 Shared Components Integration

### 1. HTML/CSS/JS kopieren
```bash  
# Desktop
cp ../shared/* desktop/src/

# Mobile  
cp ../shared/* mobile/www/
```

### 2. Platform-spezifische Anpassungen

**Desktop (main.js):**
- Fenster-Konfiguration
- Menü-Integration  
- IPC-Kommunikation
- Auto-Updater

**Mobile (mobile.js):**
- Cordova-Plugin Integration
- Touch-Optimierungen
- Mobile UI-Anpassungen
- Berechtigungshandling

### 3. Build-Scripts erstellen

**Desktop package.json scripts:**
```json
{
  "scripts": {
    "start": "electron .",
    "dev": "electron . --dev",
    "build": "electron-builder",
    "build-all": "electron-builder -mwl"
  }
}
```

**Mobile package.json scripts:**
```json
{
  "scripts": {
    "android": "cordova run android",
    "build-android": "cordova build android --release", 
    "add-plugins": "cordova prepare android"
  }
}
```

---

## 🧪 Testing & Debugging

### Desktop Testing
```bash
# Development mit DevTools
npm run dev

# Production-like testing
npm run build
# Dann Installer in dist/ ausführen
```

### Mobile Testing  
```bash
# Android Emulator
cordova emulate android

# Physisches Gerät (USB-Debugging aktiviert)
cordova run android --device

# Chrome DevTools für Debugging
# chrome://inspect → Remote Targets
```

### Cross-Platform Testing
- **Responsive Design** in Browser testen
- **WebSocket-Verbindungen** auf verschiedenen Netzwerken
- **Sprach-Features** auf echten Geräten
- **Performance** auf schwächeren Geräten

---

## 🚀 Deployment & Distribution

### Desktop Distribution
- **Windows**: `.exe` Installer, Windows Store (MSIX)
- **macOS**: `.dmg` Image, Mac App Store  
- **Linux**: `.AppImage`, `.deb`, Snap Store

### Mobile Distribution
- **Google Play Store**: AAB (App Bundle) preferred  
- **Direct APK**: Für Sideloading/Testing
- **Enterprise**: MDM Distribution

### CI/CD Setup (GitHub Actions Beispiel)
```yaml
name: Build Apps
on: [push, pull_request]
jobs:
  desktop:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - run: npm ci
      - run: npm run build-linux
      
  mobile:
    runs-on: ubuntu-latest  
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-java@v3
      - run: cordova build android --release
```

---

## 📦 Assets & Resources

### Benötigte Assets
```
assets/
├── icons/
│   ├── icon.png (Desktop - 512x512)
│   ├── tray-icon.png (Desktop - 16x16)
│   └── android/ (Mobile - verschiedene Größen)
├── splash/
│   └── android/ (Mobile Splash Screens)
└── audio/
    ├── notification.mp3
    └── success.wav
```

### Icon-Generierung
```bash
# Für Desktop (Electron)
# 512x512 PNG als Basis verwenden

# Für Mobile (Cordova)
cordova-res android --skip-config --copy
# Oder manuell alle Größen erstellen
```

---

## 🔍 Troubleshooting

### Häufige Desktop-Probleme
- **"Module not found"**: `npm install` ausführen
- **Signing-Fehler**: Code-Signing Zertifikat erforderlich
- **Performance**: Hardware-Beschleunigung aktivieren

### Häufige Mobile-Probleme  
- **Plugin-Fehler**: `cordova clean && cordova prepare`
- **Build-Fehler**: Android SDK Pfade prüfen
- **Permissions**: AndroidManifest.xml prüfen
- **Audio-Probleme**: Berechtigungen zur Laufzeit anfordern

### Debug-Tipps
```javascript
// Desktop Debug (Renderer Process)
console.log('Desktop Mode:', window.electronAPI?.isElectron);

// Mobile Debug (Cordova)
console.log('Mobile Mode:', typeof cordova !== 'undefined');
console.log('Device Info:', window.mobileApp?.getDeviceInfo());
```

---

## 📈 Performance-Optimierung

### Desktop
- **Preload Scripts** für sichere IPC
- **Main/Renderer Trennung** 
- **Memory Management**
- **Bundle-Optimierung**

### Mobile
- **WebView-Optimierung**
- **Touch-Delays reduzieren**
- **Battery-Optimierung**
- **Network-Caching**

---

Diese Anleitung deckt alle wichtigen Aspekte für die Entwicklung und Deployment beider Plattformen ab. Die modulare Struktur ermöglicht es, gemeinsame Komponenten zu teilen und platform-spezifische Features zu nutzen.
