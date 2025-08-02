# 🔐 Sicherheit

Der WebSocket-Server schützt Zugriffe über zwei Mechanismen:

1. **Token-Authentifizierung** – Clients müssen beim Verbindungsaufbau einen
   gültigen Token übergeben (`?token=...`). Der Token wird entweder direkt mit
   `WS_TOKEN` aus der Umgebung verglichen oder – falls `JWT_PUBLIC_KEY` gesetzt
   ist – als JWT verifiziert.
2. **IP-Whitelist** – nur in `ALLOWED_IPS` hinterlegte Adressen dürfen sich
   verbinden. Verstöße werden mit dem WebSocket-Close-Code `4401` und dem Grund
   `unauthorized` abgewiesen.

Die Tokenprüfung ist in `backend/ws-server/auth/token_utils.py` ausgelagert und
kann zukünftig durch eigene Module erweitert werden.
