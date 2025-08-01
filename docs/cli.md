# 🛠 Sprachassistent Setup CLI

Dieses CLI-Skript (`cli.sh`) ermöglicht dir die einfache und interaktive Installation, Konfiguration und Wartung aller Bestandteile des Sprachassistenten-Projekts.

## 📦 Voraussetzungen

* Eine `.env`-Datei im Root-Verzeichnis (kann auch interaktiv erstellt werden)
* SSH-Zugriff auf alle Remote-Geräte (Raspi 4, Raspi 400, Odroid)

## 📋 Menüoptionen

### `1)` Konfiguration ersetzen

Ersetzt alle Platzhalter in den Dateien unter `config/` anhand deiner `.env`-Datei mittels `envsubst`.

### `2)` Verbindungen testen

Prüft, ob alle Hosts erreichbar sind (Ping + HTTP) und ob der lokale WebSocket-Server antwortet.

### `3)` Alle Nodes installieren

Führt alle einzelnen Installationen nacheinander aus (Raspi4, Raspi400, Odroid, WS-Server).

### `4)` Nur Raspi 4 installieren

Installiert STT/TTS-Tools auf dem Raspi 4 (Faster-Whisper, Piper).

### `5)` Nur Raspi 400 installieren

Installiert die grafische Benutzeroberfläche für den Sprachassistenten.

### `6)` Nur Odroid installieren (Docker)

Installiert Flowise + n8n über Docker Compose auf dem Odroid.

### `7)` WebSocket-Server lokal installieren

Installiert den `ws-server.py` auf dem aktuellen System und aktiviert ihn als systemd-Dienst.

### `8)` Desktop-App bauen

Baut alle Electron-/Cordova-Apps aus `voice-assistant-apps/` mit dem Script `build_all.sh`.

### `9)` Flowise/n8n via NPM lokal installieren

Installiert Flowise und n8n direkt via `npm`, ohne Docker. Flowise wird direkt gestartet.

### `10)` Logs anzeigen

Zeigt die letzten Logzeilen des lokalen WebSocket-Servers via `journalctl`.

### `11)` Dienste neu starten

Startet den WebSocket-Server (`ws-server.service`) neu über systemd.

### `12)` .env prüfen

Prüft, ob alle benötigten Variablen in `.env` gesetzt sind. Gibt Hinweise, wenn welche fehlen.

### `13)` .env interaktiv erstellen

Erstellt eine `.env`-Datei aus der `.env.example` und fragt Werte im Terminal ab.

### `14)` Backup/Export

Exportiert Konfigurationen, .env-Datei und WS-Server als `.tar.gz` in den `backup/`-Ordner.

### `15)` Beenden

Beendet die CLI.

## 🔍 Beispielaufruf

```bash
chmod +x setup_cli.sh
./cli.sh
```

## 📁 Typische Projektstruktur

```
├── .env
├── cli.sh
├── config/
├── scripts/
├── voice-assistant-apps/
└── ws-server/
```

## ℹ️ Hinweise

* Der WS-Server verwendet Faster-Whisper und Piper lokal.
* Flowise kann sowohl lokal (npm) als auch via Docker genutzt werden.
* Headscale wird für sichere Verbindung empfohlen (`scripts/setup-headscale.sh`).

## 📞 Support

Wenn du Fragen hast, dokumentiere Fehlermeldungen und poste sie als GitHub-Issue im Projekt.
