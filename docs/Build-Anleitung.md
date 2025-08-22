# Build-Anleitung (Packaging mit electron-builder)

Diese Anleitung zeigt, wie die **Standalone Desktop-App** (Electron GUI + Python-Backend) paketiert wird.  
**Wichtig:** Diese Repo-Vorbereitung führt **keine Builds** aus. Die folgenden Kommandos sind als **später** auszuführen.

## Voraussetzungen
- Node.js ≥ 18 (empf. 20), npm ≥ 9
- Python ≥ 3.10 (empf. 3.12), `pip`, optional virtuelles Umfeld (`.venv`)
- PyInstaller (für das Backend-Binary)
- OS-spezifische Toolchain:
  - **Linux:** AppImage/deb: `electron-builder` nutzt systemweite Tools.  
  - **Windows:** NSIS Installer; Backend-Binary idealerweise **nativ** auf Windows mit PyInstaller bauen.

## Übersicht
- DEV-Modus: Electron startet `python -m ws_server.cli` direkt.
- PROD-Modus (paketiert): Electron startet das **Backend-Binary** aus `process.resourcesPath/bin/<platform>/`.

## Backend bauen (manuell, später ausführen)
> Diese Kommandos werden **hier nicht** ausgeführt – bitte später manuell starten.

**Linux:**
```bash
. .venv/bin/activate   # falls vorhanden
pip install --upgrade pip pyinstaller
pyinstaller ws_server/cli.py \
  --name ws-server --onefile --clean --noconfirm
mkdir -p voice-assistant-apps/desktop/resources/bin/linux
cp dist/ws-server voice-assistant-apps/desktop/resources/bin/linux/
chmod +x voice-assistant-apps/desktop/resources/bin/linux/ws-server
````

**Windows (PowerShell):**

```powershell
py -m pip install --upgrade pip pyinstaller
pyinstaller ws_server/cli.py --name ws-server --onefile --clean --noconfirm
mkdir voice-assistant-apps\desktop\resources\bin\win -Force
copy dist\ws-server.exe voice-assistant-apps\desktop\resources\bin\win\
```

> Passe `--add-data`/Modell-Einbindungen bei Bedarf an (z. B. Piper/Kokoro/Zonos-Modelle).

## Electron-Pakete bauen (manuell, später ausführen)

Aus dem Ordner `voice-assistant-apps/desktop`:

```bash
# Linux:
npm run dist:linux    # erzeugt AppImage & .deb
# Windows:
npm run dist:win      # erzeugt NSIS .exe
# Alle (plattformabhängig):
npm run dist
```

## GitHub Actions (optional)

Eine vorbereitete Workflow-Datei kann Builds auf Linux/Windows erstellen.
Trigger (z. B. Tags) erst setzen, wenn ihr bereit seid. Siehe `.github/workflows/release.yml`.

## ENV/Ports

* GUI ↔ Backend lokal: `WS_HOST=127.0.0.1`, `WS_PORT=48231`, `METRICS_PORT=48232`.
* In Produktion werden diese Werte im Electron-Mainprozess erzwungen.

## Troubleshooting (Kurz)

* **websockets v11+**: `handle_websocket(self, websocket, path=None)` – bereits gepatcht.
* **Token**: DEV-Token/Bypass gemäß `JWT_*` ENV im Mainprozess.
* **Binary wird nicht gefunden**: Prüfe `process.resourcesPath` und `resources/bin/<platform>/`.
* **Modelle**: Falls TTS/STT-Modelle nötig sind, entweder per `--add-data` bundlen oder zur Laufzeit laden.

## Lizensierung / Dritte

Prüfe Lizenzen von Modellen/Bibliotheken vor Distribution.
