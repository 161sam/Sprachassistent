# Hardware Setup

Die Referenzinstallation nutzt einen Raspberry Pi 4 für STT/TTS sowie einen weiteren Rechner für die Gateway-Komponenten.
Verbinde ein USB-Mikrofon und Lautsprecher mit dem Pi und installiere das System über die Skripte im Ordner `scripts/`.

## Schnellstart

1. SD-Karte mit Raspberry Pi OS beschreiben und Netzwerk einrichten.
2. Repository klonen und in das Projektverzeichnis wechseln.
3. `scripts/install_all_nodes.sh` ausführen, um Abhängigkeiten zu installieren.
4. `scripts/start-stt.sh` sowie `scripts/start-tts.sh` testen.
5. Optionale Dienste wie `ws-server` über die Install-Skripte aktivieren.

