# 🛠 Sprachassistent CLI

Das Projekt stellt eine einzige End‑User‑CLI bereit: `va`.

Beispiele:

```
# Backend starten (FastAPI/Uvicorn)
va --host 127.0.0.1 --port 48232

# Desktop (Electron) + Backend starten
va --desktop --host 127.0.0.1 --port 48232

# Modelle prüfen
va --validate-models

# Terminal‑Progress für Staged‑TTS erzwingen (0/1)
va --tts-progress 1

# Zonos lokal laden / Voice
va --zonos-local-dir models/zonos/local --zonos-model-id Zyphra/Zonos-v0.1-transformer --zonos-speaker thorsten

# Sprache (TTS)
va --language de-DE
```

Hinweis: `python -m ws_server.cli` ist veraltet und ruft intern `va` auf. Bitte künftig `va` verwenden.

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
va --help
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

### Audioausgabe & Qualität

- TTS-Geschwindigkeit wird ausschließlich im Backend angewandt (per `set_tts_options`).
  Der Player verändert `playbackRate` nicht und bewahrt die Tonhöhe (Pitch).
- Zentrale Nachbearbeitung im Manager:
  - Resampling auf `TTS_TARGET_SR` (Standard `24000`)
  - Loudness-Normalisierung (`TTS_LOUDNESS_NORMALIZE=1`) auf ≈ −16 dBFS
  - Soft-Limiter (`TTS_LIMITER_CEILING_DBFS=-1.0`)
- Staged TTS: Equal-Power Crossfade, `STAGED_TTS_CROSSFADE_MS=100` (per GUI/ENV änderbar).
- Piper: `PIPER_NOISE_SCALE=0.45`, `PIPER_NOISE_W=0.5` (ruhiger Klang)
- Zonos: `ZONOS_SPEAKING_RATE=14`, `ZONOS_PITCH_STD=0.2`
- Optionaler Binär-Audiopfad (`WS_BINARY_AUDIO=true`) bleibt standardmäßig deaktiviert; JSON‑WAV‑Chunks sind weiterhin der Default.

## 📞 Support

Wenn du Fragen hast, dokumentiere Fehlermeldungen und poste sie als GitHub-Issue im Projekt.
