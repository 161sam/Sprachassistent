Analyse der Projektstruktur und Refaktorierungsplan Sprachassistent
Identifizierte Probleme und technische Schulden

Parallele Implementierungen & Duplikate: In der Codebasis existieren mehrere parallele Versionen gleicher Funktionalität. Besonders auffällig ist dies beim WebSocket-Server – es gab unterschiedliche Varianten (z.B. ws-server.py, „enhanced“ Versionen) mit redundanten Funktionen
GitHub
. Ähnliches gilt für die Frontend-GUI, die teils doppelt in gui/ und voice-assistant-apps/shared/ gepflegt wurde
GitHub
. Diese Duplikate machen den Code unübersichtlich und führen zu Inkonsistenzen.

Ungeordnete Projektstruktur: Das Projekt wirkt chaotisch strukturiert. Viele alte Dateien liegen in archive/ und teils existieren noch Verweise darauf. Beispielsweise wird im aktuellen Server-Code Legacy-Code dynamisch geladen
GitHub
, um ältere Implementierungen weiter zu unterstützen. In Deprecations ist eine lange Liste veralteter Module aufgeführt, die durch neue ersetzt wurden
GitHub
 – dies zeigt, dass veralteter Code zwar markiert, aber noch nicht konsequent entfernt wurde. Insgesamt sind Funktionen nicht klar modularisiert, sondern verteilt und teilweise mehrfach vorhanden.

Monolithischer Code und mangelnde Modularisierung: Wesentliche Kernfunktionen liegen in sehr großen Dateien statt in getrennten Modulen. So enthält die zentrale WebSocket-Server-Datei (aktuell legacy_ws_server.py im Kompatibilitätsmodus) zahlreiche Klassen und Funktionen (STT-Streaming, Intent-Handling, TTS-Steuerung, etc.) in einem einzigen File
GitHub
. Dies erschwert das Verständnis und die Wartung. Wichtige Komponenten wie Audio-Streaming, Intent-Routing oder Authentifizierung sind nicht als separate Module gekapselt, sondern im Mischmasch implementiert.

Technische Schulden in Ein-/Ausgabe & Performance: Einige Implementierungsdetails sind suboptimal gelöst und führen zu vermeidbarer Latenz. Beispielsweise schreibt der STT-Prozess momentan Audiodaten temporär auf die Festplatte (WAV-Datei), um sie dann wieder zu laden
GitHub
 – anstatt direkt in-memory mit NumPy/PyDub zu arbeiten. Auch wurde Piper-TTS früher über einen separaten Subprozess aufgerufen
GitHub
, was Overhead erzeugt. Obwohl inzwischen ein TTSManager existiert, müssen solche Altlasten (Datei-I/O, externe Prozesse) identifiziert und eliminiert werden, um die Latenz zu senken.

Unvollständige Feature-Integration: Einige Funktionen sind erst rudimentär oder nur teilweise umgesetzt. So ist die Intent-Routing-Logik derzeit simpel (erkennt z.B. nur Wetter oder Begrüßung) und leitet komplexe Anfragen noch nicht wirklich an Flowise oder n8n weiter
GitHub
, obwohl die Doku dies vorsieht. Auch das lokale Skill-System und ein Intent-Klassifizierer sind zwar angedacht
GitHub
, aber im Code nur als Platzhalter (z.B. Dummy-Klassen in IntentClassifier und leere skills.load_all_skills Rückgaben
GitHub
GitHub
). Diese teils unfertigen Features mindern derzeit die Funktionalität und Qualität der Anwendung.

Inkonsistente Benennung und Legacy-Konfusion: Durch die vielen Entwicklungsiterationen gibt es historische Namensreste wie “v1”, “v2”, “enhanced”, etc. innerhalb des Projekts. Dies kann neue Entwickler verwirren. In den Guidelines wird ausdrücklich empfohlen, solche Suffixe zu vermeiden und obsoleten Code klar zu archivieren
GitHub
. Momentan finden sich jedoch z.B. Verweise auf „binary v2“ parallel zu JSON v1 im Protokoll
GitHub
 und Dateien wie ws_server_old.py, ws_server_enhanced.py im Archiv. Diese Mischung erschwert die Wartung und birgt Risiko, versehentlich alte Komponenten zu verwenden.

Geringe Testabdeckung und potenzielle Stabilitätsprobleme: Automatisierte Tests sind kaum vorhanden; nur vereinzelte manuelle Testskripte existieren. Fehlendes Testing erschwert Refaktorierungen, da nicht sofort ersichtlich ist, ob bestehende Features intakt bleiben
GitHub
. Zudem gibt es verbesserungswürdige Fehlerbehandlung – etwa sollte der WebSocket-Server robustere Retry-Mechanismen und Client-Reconnects unterstützen
GitHub
. Ohne solche Maßnahmen kann es bei Netzwerkfehlern zu hängenden Verbindungen oder Abstürzen kommen, was die Zuverlässigkeit beeinträchtigt.

Plan zur Behebung der Probleme (Refactoring)

Duplikate konsolidieren: Zusammenführung paralleler Implementierungen zu einer einzigen Codebasis. Insbesondere wird der WebSocket-Server vollständig vereinheitlicht, indem alle Funktionen aus den historischen Varianten in den aktuellen Server übernommen werden
GitHub
. Veraltete Dateien (z.B. ws-server-old.py, ws-server-enhanced.py) können dann gelöscht oder endgültig ins Archiv verschoben werden, sodass kein produktiver Code mehr darauf zeigt. Ebenso im Frontend: Die doppelte GUI-Codebasis wird aufgelöst, indem man die neue Web-GUI (aktuell z.B. gui/index.html als modernere Variante) und die shared Komponenten verschmilzt und nur eine Quelle für alle Clients pflegt
GitHub
.

Projektstruktur aufräumen und vereinheitlichen: Einführung einer klaren Ordner- und Modulstruktur, um Chaos zu beseitigen. Der Backend-Code sollte in einen konsistenten Namespace (z.B. backend/ oder direkt ws_server/) überführt werden, anstatt verteilt in backend, ws_server, archive und root-Skripte. Eine mögliche Zielstruktur ist in der Dokumentation skizziert – mit Unterordnern für Audio, Routing, Auth, Config etc.
GitHub
GitHub
. Konkret heißt das: Audio-Verarbeitung (Streaming, VAD, STT/TTS-Engine) in ein eigenes Paket, Intent-Routing/Skills in ein eigenes Modul, Authentifizierung/Token-Handhabung separat, und einen klaren zentralen Einstiegspunkt für den Server. Dieses Reorganisieren beseitigt viele technische Schulden, da zusammengehörige Funktionen gebündelt und unnötige Verschachtelungen entfernt werden.

Obsoleten Code entfernen oder isolieren: Alle nicht mehr benötigten Altlasten sollten identifiziert werden. Code, der durch neue Implementierungen überflüssig wurde, wird gelöscht oder zumindest in ein klar gekennzeichnetes archive/ verschoben (und aus dem Build/Import-Pfad verbannt). Beispielsweise können alte Skills-/Intent-Klassifier-Dateien aus früheren Experimenten, die derzeit nur Dummy-Funktionen liefern, entfernt werden, sobald ein neues Skillsystem greift. Dadurch verringert sich die Verwirrung und der aktive Codeumfang. Wichtig: Dabei alle bestehenden Features erhalten, außer sie werden durch eine neue Implementierung ersetzt (d.h. keine funktionalen Einschnitte für den Nutzer). Die Deprecation-Tabelle
GitHub
 dient hier als Leitfaden, was schon ersetzt wurde – diese Stellen müssen nachgezogen und Altcode entsorgt werden.

Modularisierung und Aufteilung großer Komponenten: Der monolithische WebSocket-Server-Code wird in logische Module zerlegt. Z.B. eine Klasse AudioStreamManager und der VAD kommen in audio/streaming.py, die STT-Logik (AsyncSTTEngine) in audio/stt_engine.py, die TTS-Logik in audio/tts_engine.py usw.
GitHub
. Die Intent-Routing-Entscheidung (_generate_response) wandert in eine eigene Komponente, etwa routing/intent_router.py, welche je nach Intent entscheidet, ob ein lokaler Skill, der LLM-Agent (Flowise) oder ein n8n-Workflow aufgerufen wird. Auch eine Vorbereitung für Auth (z.B. auth/token_utils.py und perspektivisch auth/rate_limiter.py) ist sinnvoll, selbst wenn Auth jetzt noch einfach ist
GitHub
. Diese Trennung verbessert die Lesbarkeit enorm und erlaubt es, einzelne Teile unabhängig weiterzuentwickeln oder auszutauschen, ohne die ganze Datei anfassen zu müssen
GitHub
.

Konfiguration und Naming konsistent gestalten: Einführung einer zentralen Konfigurationsverwaltung (z.B. mit einer config/settings.py oder Nutzung von .env via Pydantic Settings) stellt sicher, dass alle Module die gleichen Einstellungen nutzen
GitHub
. Dabei alle alten ENV-Variablen prüfen und vereinheitlichen (z.B. nur noch WS_PORT statt verstreuter Port-Konstanten). Zudem die Benennung vereinheitlichen: keine verwirrenden Suffixe wie v2 oder enhanced mehr im aktiven Code. Stattdessen klare Klassen-/Dateinamen, die den Zweck beschreiben (z.B. VoiceServer als Haupt-Serverklasse, IntentRouter, TTSManager etc.). Dieser Schritt reduziert kognitive Last und folgt den eigenen Guidelines
GitHub
.

Leistungshungrige Teile optimieren: Behebung der identifizierten ineffizienten Stellen im Code. Insbesondere muss die STT-Verarbeitung komplett auf In-Memory umgestellt werden – das heißt, Audiobuffer direkt als NumPy-Array an Whisper weitergeben, ohne temporäre Dateien
GitHub
. Die Implementierung von AsyncSTTEngine._transcribe_sync kann dahingehend angepasst werden, wie es im Architekturvorschlag bereits angedacht ist (Konvertierung des Byte-Streams zu NumPy und WhisperModel direkt aufrufen)
GitHub
GitHub
. Ebenso sollte Piper nicht mehr via externem piper-CLI aufgerufen werden, sondern über das Python-Modul (z.B. piper-tts-python) innerhalb des TTSManagers laufen
GitHub
. Dadurch spart man Prozessstartzeit und kann Geschwindigkeit/Stimme direkt als Parameter übergeben. Insgesamt sorgen diese Optimierungen für spürbar geringere Latenz und CPU-Overhead.

Feature-Funktionalität fertigstellen: Die begonnenen, aber unvollendeten Features werden zu Ende implementiert. Konkret: Intent-Routing – Die Umgebungsvariablen FLOWISE_URL/FLOWISE_ID und N8N_URL sollten tatsächlich genutzt werden, um bei bestimmten erkannten Intents HTTP-Aufrufe an Flowise (LLM-Agent) bzw. n8n zu machen
GitHub
. Hierfür wird im IntentRouter hinterlegt, welche Keywords/Intents komplexe KI-Fragen darstellen (z.B. „openai_question“) vs. lokale Befehle, und entsprechend die Request an den externen Dienst abgesetzt. Lokale Skills – Entwicklung eines einfachen Plug-in-Systems, das Skills (z.B. Python-Module in einem skills/ Ordner) lädt und deren Funktionen bei bestimmten Intents ausführt. So können Offline-Funktionen (Smart-Home-Steuerung, Medienwiedergabe etc.) implementiert werden, die ohne Cloud auskommen
GitHub
. Intent-Classifier – Integration eines kleinen NLP-Modells oder regelbasierten Systems, das eingehende Texte grob einer Intent-Kategorie zuordnet, um das Routing zu unterstützen (z.B. Konfidenzwerte für „ist wahrscheinlich eine Wissensfrage“). Diese Komponenten stellen sicher, dass alle im Konzept beschriebenen Routen (einfacher Befehl vs. komplexe Frage vs. Automation) wirklich funktionieren und nicht nur als Platzhalter im Code stehen.

Verbesserte Fehlerbehandlung und Tests einführen: Um die Stabilität zu erhöhen, wird der WebSocket-Server mit robustem Error-Handling ausgestattet. Beispielsweise kann in der Empfangsschleife von handle_websocket ein Retry-Mechanismus implementiert werden, der bei temporären Netzwerkproblemen einen erneuten Sendeversuch unternimmt
GitHub
. Auch sollte auf Client-Seite ein automatischer Reconnect (mit Exponential Backoff) unterstützt werden, falls die Verbindung abreißt
GitHub
. Zusätzlich sind Unit-Tests für die Kernbereiche unerlässlich: Tests für Audio-Streaming (korrekte Zerlegung und Weiterleitung von Audiopaketen), für Intent-Routing-Entscheidungen (z.B. dass „Wetter“ den richtigen Pfad nimmt), für den TTS-Manager (verschiedene Engines liefern Erfolg) etc.
GitHub
. Eine kontinuierliche Integration mit diesen Tests stellt zukünftig sicher, dass Refaktorierungen keine alten Features brechen. Ebenso sollten Performance- und Speichertests durchgeführt werden, um Memory Leaks oder Latenz-Einbrüche früh zu erkennen.

Entwicklungsplan für zukünftige Erweiterungen und Optimierungen

Nach der Bereinigung des bestehenden Codes soll das Sprachassistent-Projekt mit Fokus auf geringer Latenz, hoher Sprachqualität, Robustheit und neuen Features ausgebaut werden. Im Folgenden die Schwerpunkte der Weiterentwicklung:

Latenzoptimierung: Die Antwortzeit des Systems soll weiter verkürzt werden, sodass Sprachinteraktion in Echtzeit möglich ist. Geplante Maßnahmen umfassen asynchrone Audioverarbeitung und Streaming in kleineren Häppchen. Beispielsweise kann die WebSocket-Übertragung auf kleinere Audio-Chunks (z.B. 512–1024 Bytes) in höherer Frequenz umgestellt werden und schon während der Aufnahme verarbeitet werden
GitHub
GitHub
. Ein zweistufiges TTS-Verfahren (Staged TTS) ist bereits prototypisch vorhanden, bei dem ein kurzer Piper-„Intro“-Satz sofort abgespielt wird, während parallel die hochwertigere Zonos-Stimme längere Passagen generiert
GitHub
. Dieses Konzept soll weiter verfeinert werden – z.B. durch dynamisches Chunking langer Antworten und Crossfades beim Übergang der Stimmen, um Wartezeiten kaum spürbar zu machen. Auch auf STT-Seite könnte eine Streaming-Transkription erwogen werden, bei der laufende Audioeingaben fortlaufend zu Text verarbeitet werden (Whisper unterstützt z.B. auch segmentweises Transkribieren), sodass die Antwortgenerierung früher starten kann. Zudem wird geprüft, ob Hardware-Beschleunigung besser genutzt werden kann: Auf einem Desktop/Server könnte man größere Whisper-Modelle auf der GPU laufen lassen, während auf dem Pi kleinere Modelle für schnellere Ergebnisse genutzt werden – ggf. mit automatischem Model-Switch je nach Länge/Komplexität der Anfrage. All diese Optimierungen zielen darauf ab, die Systemlatenz von der Spracherkennung bis zur Ausgabe unter realen Bedingungen so gering wie möglich zu halten (idealerweise deutlich unter 1 Sekunde für kurze Anfragen).

Steigerung der Sprachqualität: Die Natürlichkeit und Verständlichkeit der Sprachausgabe soll weiter erhöht werden. Hier steht TTS-Qualität im Vordergrund. Zunächst werden die vorhandenen Engines (Piper, Kokoro, Zonos) optimal konfiguriert: Nutzung hochqualitativer Modelle (z.B. größere Voice-Modelle für Zonos, feinjustierte deutsche Stimmen für Piper) und automatische Sprachauswahl je nach Eingabesprache
GitHub
. Geplant ist auch eine automatische Stimmoptimierung – das System könnte z.B. die TTS-Parameter wie Sprechgeschwindigkeit oder Tonhöhe kontextabhängig anpassen (schneller bei langen Erklärungen, klarer bei lauter Umgebung). „Automatic voice tuning“ bedeutet auch, das TTS-Ausgabeprofil an den Nutzer anzupassen: eventuell mittels Equalizer oder Filter, um in verschiedenen Räumen gut verständlich zu sein, oder sogar eine personalisierte Stimme zu ermöglichen. Auf STT-Seite wird die Erkennungsqualität gesteigert, indem z.B. Rauschentfernung und VAD verbessert werden. Ein automatisches Mikrofon-Tuning kann hinzu kommen – etwa Kalibrierung der Eingabelautstärke und Empfindlichkeit (AGC), damit unterschiedlich laute Sprecher gleich gut erkannt werden. Ebenso denkbar ist der Einsatz von Sprachmodell-Nachbearbeitung, um erkannte Texte zu verbessern (z.B. automatisches Hinzufügen von Satzzeichen oder Korrektur von bekannten Erkennungsfehlern durch ein kleines NLP-Modul). Ziel all dieser Maßnahmen ist ein ultra-realistische Sprachausgabe und eine sehr zuverlässige Erkennung, sodass der Assistent so natürlich wie möglich wirkt.

System-Härtung und Skalierbarkeit: Im produktiven Einsatz muss das System robust und sicher laufen. Daher werden zusätzliche Hardening-Schritte unternommen. Geplant ist die Einführung einer Token-basierten Authentifizierung für die WebSocket-Verbindung (z.B. via JWT), um unautorisierte Zugriffe zu verhindern, besonders wenn der Server über Netzwerk erreichbar ist
GitHub
. Ergänzend wird ein Rate Limiting implementiert, um Missbrauch (zu viele Anfragen in kurzer Zeit) zu unterbinden
GitHub
 – wichtig sowohl für Sicherheit als auch um die Hardware (Pi) nicht zu überlasten. Auch der vorhandene VPN-Ansatz (Headscale) wird integriert geprüft, damit die Kommunikation zwischen den verteilten Komponenten abgesichert ist. Weiterhin steht Monitoring im Fokus: Die Metrik-Schnittstelle (Port 48232) liefert bereits Basisdaten; diese sollen in ein Monitoring-System (z.B. Prometheus/Grafana) eingespeist werden, um Latenzen, Auslastung und Fehler zentral zu überwachen. Für die Stabilität sorgen auch intensives Testing (Stresstests, Langzeittests über Tage, um Memory Leaks aufzudecken) und eine CI/CD-Pipeline, die automatisch Builds und Tests durchführt. Schließlich wird die Plattform-Unabhängigkeit geprüft und verbessert – das Backend soll auf verschiedenen Hardware (Raspberry Pi, Odroid, x86-Server) gleich stabil laufen. Wo nötig, werden Optimierungen je Plattform vorgenommen (z.B. alternative TTS-Modelle für ARM). All diese Schritte machen den Sprachassistenten robust gegen Ausfälle und einsatzbereit für den Dauerbetrieb.

Neue Features und Erweiterungen: Um das System attraktiver und hilfreicher zu machen, werden nach dem Refactoring neue Funktionen hinzugefügt. Lokale Skills sollen ausgebaut werden – etwa Module für Smart-Home-Steuerung, Musik abspielen, Terminverwaltung etc., die offline funktionieren. Gleichzeitig wird die Agent-Integration vertieft: Der LLM-Agent (über Flowise) könnte mit Tools erweitert werden, z.B. einer Fähigkeit, Web-Suchen durchzuführen, um Fragen mit aktuellen Informationen zu beantworten. Dadurch kann der Assistent nicht nur vordefinierte Antworten geben, sondern auch eigenständig Informationen suchen und finden (“search/find new features”). Geplante ist zudem eine Verbesserung der Multi-User-Unterstützung: Der Assistent könnte Stimmen erkennen und unterschiedliche Profile pro Nutzer verwenden (z.B. verschiedene Wake-Words oder persönliche Präferenzen pro Nutzer). Die Cross-Plattform-Clients (Desktop, Mobile, Web) werden um neue Bedienungsfeatures ergänzt – z.B. Push-Benachrichtigungen bei bestimmten Ereignissen, eine verbesserte Offline-Nutzung auf Mobile, oder ein Setup-Wizard in der Desktop-App, um die Ersteinrichtung zu erleichtern. Auch ein All-in-One Modus wird angestrebt: Das System soll so paketiert werden, dass eine Nutzerin es auf einem einzigen Gerät leicht installieren und starten kann. Im Desktop-Client wird dafür der Python-Backend-Server bereits als Binary mitgeliefert
GitHub
 – diese Integration wird weiter verfeinert, sodass der “Server” für Hobby-Anwender unsichtbar im Hintergrund der Desktop-App läuft. Später kann dieses All-in-One-Konzept auch auf Raspberry Pi und Mobile adaptiert werden (z.B. ein Raspberry Pi Image, das Backend und Web-GUI enthält, oder eine mobile App, die im lokalen Modus arbeiten kann). Schließlich steht die kontinuierliche Verbesserung auf der Agenda: Das Projekt wird regelmäßig nach neuen sinnvollen Features durchsucht – z.B. Unterstützung weiterer Sprachen, Integration neuer STT/TTS-Modelle aus der Open-Source-Community, oder Verbesserungen der Benutzeroberfläche – und diese werden in kurzen Iterationen hinzugefügt. Durch diese agile Weiterentwicklung bleibt der Sprachassistent technisch aktuell und kann mit kommerziellen Lösungen mithalten.

Fazit: Durch die gründliche Bereinigung der Altlasten und eine strategische Weiterentwicklung entlang der genannten Schwerpunkte wird das Sprachassistent-System deutlich wartbarer, leistungsfähiger und funktionsreicher. Alle bestehenden Kernfunktionen bleiben erhalten (außer dort, wo neue Implementierungen eine alte überflüssig machen), sodass kein Feature-Verlust eintritt
GitHub
. Gleichzeitig legen die geplanten Refaktorierungen und Optimierungen das Fundament für beste Sprachqualität, minimalste Verzögerungen und eine stabile, erweiterbare Plattform, auf der in Zukunft noch viele innovative Features aufgebaut werden können. Mit diesem Entwicklungsplan wird aus dem momentan unübersichtlichen Prototyp ein robustes, modernes All-in-One-Sprachassistenzsystem für Desktop, Raspberry Pi und mobile Geräte.

Sources: Die Analyse und Empfehlungen basieren auf dem aktuellen Projektcode und begleitenden Dokumenten, inkl. den Deprecation-Hinweisen
GitHub
, Code-Review-Empfehlungen
GitHub
GitHub
 und Architekturplänen
GitHub
GitHub
 des Repositories. Diese belegen die vorhandenen Probleme und skizzieren bereits viele der hier vorgeschlagenen Lösungswege.
