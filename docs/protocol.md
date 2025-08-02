# 📡 Verbindungsprotokoll

Fällt die WebSocket-Verbindung aus, sollte der Client automatisch einen
Reconnect versuchen. Empfohlener Algorithmus:

```
backoff = 1
while not connected:
    warten(backoff Sekunden)
    backoff = min(backoff * 2, 30)
```

Nach jeder fehlgeschlagenen Verbindung wird der Backoff verdoppelt und auf
maximal 30 Sekunden begrenzt.
