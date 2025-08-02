# Code- und Dokumentationsreview

## Backend (Server & Engine Optimierung)

### Parallelle WebSocket-Server zusammenführen
Derzeit existieren mehrere Varianten des WebSocket-Audiostreaming-Servers (z. B. ws-server.py vs. ws-server-with-tts-switching.py sowie archivierte Versionen) mit redundanter Funktionalität. Konsolidiere diese zu einer einzigen Implementierung. Insbesondere sollten die in ws-server-with-tts-switching.py enthaltenen Features (etwa dynamisches TTS-Engine-Switching) in den Haupt-WebSocket-Server übernommen und doppelte Altcodes entfernt werden. 
- **Begründung:** Ein einheitlicher Server vereinfacht Wartung und verhindert Inkonsistenzen.

### Unvollständige Routing-Logik ergänzen
Implementiere die in der Dokumentation vorgesehene Entscheidungslogik zur Weiterleitung komplexer Anfragen an Flowise oder n8n. Derzeit ist die Intent-Routing-Logik im WebSocket-Server nur rudimentär (Zeit/Begrüßung/Dank-Erkennung, sonst Echo) und Aufrufe an externe Dienste fehlen. 
- Baue an entsprechender Stelle (z. B. in _generate_response) die Nutzung von FLOWISE_URL / FLOWISE_ID und N8N_URL aus der Konfiguration ein, um erkannte Intents via HTTP an Flowise-Agent oder n8n Workflow weiterzugeben. 
- **Begründung:** Stellt sicher, dass komplexe Anfragen wie vorgesehen an KI-Services und Automations-Workflows delegiert werden, statt nur statisch beantwortet zu werden.

### Fehlerbehandlung & Stabilität im WebSocket-Server verbessern
Füge robustere Error-Handling-Mechanismen hinzu. 
- Z. B. in der Connection-Handling-Schleife bei handle_websocket ggf. Wiederholungsversuche einbauen, um transienten Fehlern zu begegnen (siehe Entwurf eines Retry-Mechanismus in den Projekt-Notizen). 
- Außerdem sicherstellen, dass im Fehlerfall die Verbindung nicht hängen bleibt: In ConnectionManager.send_to_client werden geschlossene Verbindungen bereits ausgetragen, aber ein automatischer Reconnect auf Client-Seite (Exponential Backoff) sollte unterstützt werden. 
- **Begründung:** Erhöht die Zuverlässigkeit bei Netzwerkstörungen und verhindert Verbindungsabbrüche ohne Wiederverbindungsversuch.

### Performance-Optimierung STT-Verarbeitung
Vermeide die Nutzung temporärer Dateien für die Spracherkennung. Derzeit schreibt AsyncSTTEngine._transcribe_sync Audiodaten in eine .wav-Datei und lädt sie dann für Whisper. 
- Besser direkt in Memory arbeiten – z. B. das Byte-Array in ein NumPy-Array umwandeln und an WhisperModel.transcribe übergeben (so ähnlich im Architektur-Vorschlag skizziert). 
- **Begründung:** Spart Datei-I/O und beschleunigt die Transkription erheblich, was die Gesamtlatenz senkt.

### TTS-Engine-Einsatz optimieren
Integriere TTS-Einstellungen aus der Konfiguration (Sprache, Stimme, Geschwindigkeit, Lautstärke aus .env bzw. env-Variablen) in die Synthese. 
- Aktuell verwendet die ältere Implementierung z.B. Piper per Subprozess-Aufruf mit festem Modellpfad. In der neuen modularen TTS-Engine (backend/tts) sind bereits Parameter für Stimme und Geschwindigkeit vorgesehen – stelle sicher, dass diese über WebSocket-Befehle (tts_engine, tts_voice Felder im JSON) gesetzt und im Backend umgesetzt werden. 
- Zudem sollte anstelle eines externen piper -CLI-Aufrufs die Python-Bibliothek (piper tts) direkt verwendet werden, um Overhead zu reduzieren. 
- **Begründung:** Erlaubt flexible Stimmwahl (z. B. zwischen deutschen Piper-Stimmen und englischen Kokoro-Stimmen) und Echtzeit-Anpassung der Sprechgeschwindigkeit, verbessert Performance und reduziert Abhängigkeiten von externen Prozessen.

### Code-Struktur modularisieren
Refaktoriere den Backend-Code in logisch getrennte Module gemäß den Best-Practice-Vorschlägen. Beispielsweise können Audio-Streaming, Intent-Routing und Authentifizierung in eigene Unterpakete ausgelagert werden. 
- Aktuell sind viele Klassen und Funktionen in einer Datei (ws-server.py) konzentriert, was die Lesbarkeit erschwert. Teile den Code auf: z. B. audio/streaming.py (für AudioStreamManager und Audiopuffer), audio/stt_engine.py, audio/tts_engine.py, routing/intent_router.py (für die Logik aus _generate_response), sowie ein auth/ -Modul für zukünftige Authentifizierung (z. B. Token-Handling, Rate Limiting). 
- **Begründung:** Eine klare Trennung nach Verantwortlichkeiten erhöht die Wartbarkeit und erleichtert künftige Erweiterungen (etwa Austausch der STT-Engine oder Hinzufügen von Auth, ohne die Hauptdatei zu verändern).

### Testabdeckung erhöhen
Schreibe unit tests für Kernkomponenten des Backends. 
- Einige manuelle Test-Skripte existieren bereits (z. B. backend/test_tts_system.py testet TTS Engines), dennoch sollten automatisierte Tests für den WebSocket-Server (Verbindungs-Handling, Intent-Routing-Entscheidungen, Fehlersituationen) erstellt werden. 
- **Begründung:** Ein solides Testset stellt sicher, dass Refaktorierungen und Erweiterungen (wie die oben genannten) keine bestehenden Funktionen brechen.

## Frontend (GUI & Client-Apps)

### Einheitliche GUI-Codebasis
Zusammenführen der aktuell parallelen GUI-Implementierungen in eine gemeinsame Codebasis. Konkret sollte der Web-Frontend-Code (index.html, app.js, styles.css in gui/) in den Ordner voice-assistant-apps/shared/ überführt werden, sodass Desktop (Electron) und Mobile (Cordova) darauf zugreifen können. 
- Die Build-Skripte kopieren bereits shared -Dateien in die jeweiligen Plattformordner; langfristig sollte jedoch vermieden werden, dass zwei unterschiedliche Stellen (z. B. gui/ und shared/) gepflegt werden müssen. Entferne Dubletten wie gui/index-new.html (neue Version) vs. gui/index.html (alte Version), indem Du die neuere, optimierte HTML als alleinige Grundlage nimmst. 
- **Begründung:** Eine konsolidierte Frontend-Codebasis garantiert ein konsistentes Nutzererlebnis und reduziert den Wartungsaufwand erheblich.

### Veraltete Komponenten und Assets bereinigen
Identifiziere und entferne alte oder unbenutzte UI-Elemente. Beispielsweise deutet der Sofortige Aktionsplan darauf hin, dass es vorherige GUI-Varianten gab (eine ältere index.html und globale JS, evtl. ohne Performance Optimierungen). 
- Stelle sicher, dass keine Referenzen mehr auf nicht vorhandene Pfade wie voice-assistant-apps/shared/core/VoiceAssistantCore.js ins Leere laufen (der Service Worker listet solche Pfade zum Cachen auf). 
- Alle tatsächlich benötigten JS-Module (z. B. OptimizedAudioStreamer.js, EnhancedVoiceAssistant/VoiceAssistantCore.js) müssen im Repository vorhanden und im finalen Build referenziert sein – falls sie noch fehlen, implementiere sie oder passe die Pfade an. 
- **Begründung:** Tote Links und alte Dateien können zu Laufzeitfehlern führen (PWA-Cache könnte fehlschlagen) und erschweren neuen Entwicklern das Verständnis der aktuellen Codebasis.

### Cordova-/Electron-spezifische Integration prüfen
Sicherstellen, dass die plattformspezifischen Funktionen in Mobile und Desktop weiterhin reibungslos funktionieren, nachdem der UI-Code vereinheitlicht wurde. 
- Zum Beispiel müssen Cordova-Plugins für Mikrofonzugriff und Hintergrundmodus in die neue GUI integriert werden (evtl. via mobile.js oder direkt in app.js mit Cordova-Abfragen). 
- Ebenso sollte die Electron-App (Desktop) weiterhin native Menüs, Tray-Icon, Autostart etc. bereitstellen – diese sind derzeit vermutlich in desktop/src/main.js oder ähnlichen Dateien konfiguriert. 
- Ggf. in der Dokumentation erwähnte Features wie Push Notifications und Background Mode (Mobile) oder Auto-Updater (Desktop) in die neue Struktur übernehmen und testen. 
- **Begründung:** Nach der Zusammenführung der GUI darf keine Plattform Funktionalität verlieren. Alle besonderen Features der Desktop- und Mobile-App müssen nachgezogen oder neu implementiert werden, damit die Apps weiterhin den beschriebenen Umfang abdecken.

### Performance und UX verfeinern
Überprüfe die Client-App auf mögliche Optimierungen: 
- **Streaming-Effizienz:** Die GUI sendet aktuell Audiopakete in 50ms-Intervallen mit 1024 Bytes Chunkgröße. Teste, ob diese Werte optimal sind für verschiedene Geräte; ggf. dynamische Anpassung (adaptiveQuality) nutzen oder per Einstellung zugänglich machen. 
- **Hintergrund-Tasks:** Implementiere den Audio-Worklet (audio-streaming-worklet.js), falls geplant, um Audiobearbeitung vom Main-Thread zu entkoppeln. 
- Der Service Worker und WebWorker werden bereits vorgesehen (Offline-Sync, Push in sw.js); stelle sicher, dass z. B. doBackgroundSync() tatsächlich Nachrichten speichert und später sendet, oder dokumentiere die Nutzung. 
- **UI-Feedback:** Ergänze visuelle Hinweise für Verbindungsstatus und Reconnect-Versuche. Die GUI hat ein autoReconnect -Flag in den Settings, aber ein Nutzer sollte auch sehen, wenn die Verbindung verloren ging und die App versucht, neu zu verbinden (z. B. via Statusbalken oder Toast-Nachricht). 
- **Mobile UX:** Wende kurzfristig die im Aktionsplan genannten Mobile-Optimierungen an – z. B. größere Touch-Flächen und Safe-Area-Abstände für Bedienelemente am unteren Rand sowie Touch-Gesten (Swipe nach oben zum Starten der Aufnahme, unten zum Stoppen). Diese CSS- und JS-Anpassungen sollten in die bestehenden Styles und Event Listener integriert werden. 
- **Begründung:** Verbesserte Performance (geringere Latenz, flüssigere Animationen) und Usability insbesondere auf Mobilgeräten erhöhen die Akzeptanz der Anwendung. Zudem verhindern klare Statusanzeigen und Fehlermeldungen, dass der Nutzer bei Verbindungsproblemen im Unklaren gelassen wird.

### Best Practices im Frontend umsetzen
Achte auf sauberen, wartbaren UI-Code. Insbesondere: 
- **Zustandsverwaltung:** Erwäge, die GUI-Logik (Aufnahmezustand, Einstellungen) in einem zentralen Objekt zu halten – aktuell existiert bereits voiceAssistantGUI.settings und entsprechende Methoden. Stelle sicher, dass bei Änderungen (z. B. toggleSetting) der Zustand konsistent bleibt und ggf. in localStorage persistiert wird, damit Einstellungen bei Neustart erhalten bleiben. 
- **Zugänglichkeit:** Überprüfe index.html auf semantisch korrekte Elemente (Buttons für klickbare Icons mit aria-label, ausreichende Kontraste etc.). Zum Beispiel der Mikrofon Button <span id=\"voiceIcon\">🎙</span> sollte für Screenreader zugänglich sein. 
- **Cleanup:** Schließe event listeners und Intervalle sauber. In VoiceAssistantGUI werden Intervalle (recordingTimer, Performance-Monitoring Interval) gestartet – sorge dafür, dass diese beim Navigationswechsel oder App-Pause gestoppt werden, um Speicherlecks zu vermeiden (z. B. Cordova Pause/Resume Events behandeln). 
- **Begründung:** Sauberer Frontend-Code erleichtert zukünftige Änderungen (etwa die geplante Unterstützung einer iOS-App) und stellt sicher, dass die App auch unter verschiedenen Bedingungen (Accessibility, App-Lifecycle) korrekt funktioniert.

## Neue Features & Architekturanpassungen (Vorschläge)

### Benutzer-Authentifizierung und Sicherheit
Einführung eines optionalen Auth-Tokens oder JWT Authentifizierung für die WebSocket-Verbindung und API-Endpoints. 
- Derzeit schützt ein statischer Token in .env (WS_TOKEN) den n8n-Webhook, aber der WebSocket selbst könnte ebenfalls eine Token- oder OAuth-basierte Authentifizierung erhalten. In der zukünftigen Struktur sind Module für Auth (JWT, Refresh Tokens) und Rate Limiting vorgesehen – diese Konzepte könnten schrittweise eingebaut werden. 
- Vorschlag: Implementiere einen Auth-Handshake bei Verbindungsaufbau (Client sendet Token, Server verifiziert bevor er Streaming zulässt) und nutze IP-Whitelist (ALLOWED_IPS aus .env) im Server, um unautorisierte Zugriffe abzulehnen.

### Erweiterbares Skill-System
Derzeit sind lokale Skills nur als Hardcoded-Logik im Code umgesetzt. 
- Es wäre besser, ein Plugin-System zu haben, bei dem neue Fähigkeiten ohne Code-Änderung hinzugefügt werden können. 
- Vorschlag: Implementiere ein Skill-Interface (z. B. jede Python-Klasse in einem skills/ Verzeichnis mit einer handle_intent Methode). Diese können dynamisch geladen und in einer Intent-Mapping registriert werden (z. B. via Config-Datei oder Konvention). 
- Die Dokumentation deutet so etwas bereits an (Beispiel einer INTENTS Mapping in docs/skill-system.md) – dies ließe sich mit wenig Aufwand realisieren, indem _generate_response statt festen if-Abfragen eine solche Mapping-Tabelle nutzt. 
- **Begründung:** Erhöht die Wartbarkeit und ermöglicht Community-Beiträge, ohne den Kernserver zu verändern.

### Fortschrittlichere Intent-Erkennung
Perspektivisch sollte die Schlagwort-Erkennung durch einen ML-basierten Intent Classifier ergänzt werden. 
- Dies ist bereits in der Roadmap (Version 2.2.0: “Advanced Intent Classification (ML-based)”) vorgesehen. 
- Vorschlag: Integriere eine schlanke Natural Language Understanding Komponente – z. B. fastText oder eine kleine Transformer-Modell – die den Transkript-Text klassifiziert (Domain-Intents vs. Freitext). 
- Das Ergebnis könnte dann entscheiden, ob lokal (bekannter Intent) oder via LLM (Flowise) geantwortet wird. 
- **Begründung:** Erhöht die Erkennungsrate und Flexibilität des Assistenten, insbesondere wenn Phrasen nicht exakt einem Schlüsselwort entsprechen.

### Modernisierung des Server-Frameworks
Ziehe in Betracht, den Python-Backend-Server auf FastAPI umzustellen, um WebSocket- und HTTP-Funktionalität un...
