# 🌐 Server API

## WebSocket `/ws`

Verbindung: `ws://<host>:8000/ws?token=<TOKEN>`

* akzeptiert Audio- und Textnachrichten wie im alten Protokoll
* bei ungültigem Token oder IP wird die Verbindung mit Code `4401` beendet

## GET `/metrics`

Gibt einfache Serverstatistiken als JSON zurück.

## POST `/debug/restart`

Platzhalter-Endpunkt für zukünftige Hot-Restarts während der Entwicklung.
