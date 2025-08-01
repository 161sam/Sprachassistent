# Development Guide

Dieses Projekt verwendet Node.js für die GUI und Python für den WebSocket-Server.
Installiere die Abhängigkeiten mit `npm install` bzw. `pip install -r requirements.txt` und nutze die Skripte im `scripts/` Ordner für das Setup.

## Entwicklungsablauf

1. `gui/index.html` im Browser öffnen und mit `node gui/app.js` einen lokalen Server starten, falls benötigt.
2. Den Python WebSocket-Server mit `python ws-server/ws-server.py` ausführen.
3. Änderungen an HTML/CSS laden automatisch neu, bei Python wird ein Neustart empfohlen.
4. Für Desktop-Tests steht im Ordner `voice-assistant-apps/desktop` eine minimale Electron-Umgebung bereit.

Weitere Details zu Build-Varianten findest du in der [Build-Anleitung](Build-Anleitung.md).

