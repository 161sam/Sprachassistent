# Skill-System

Dieses Projekt nutzt ein einfaches Intent-Routing. Für erkannte Schlüsselwörter werden lokale
oder entfernte Aktionen ausgeführt. Die Implementierung erfolgt im WebSocket-Server
(`ws-server/ws-server.py`). Eigene Skills lassen sich dort leicht erweitern.

## Eigene Skills anlegen

1. Im Ordner `ws-server` eine neue Python-Datei erstellen oder bestehende Funktionen erweitern.
2. Den Intent-Namen in der Mapping-Tabelle des WebSocket-Servers registrieren.
3. Die Funktion sollte einen Text zurückgeben, der an die GUI gesendet wird.

Beispiel:

```python
INTENTS = {
    "wetter": my_weather_skill,
}

def my_weather_skill(text: str) -> str:
    return "Heute bleibt es trocken mit 20°C"
```

