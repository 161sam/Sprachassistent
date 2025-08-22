# 🧑‍💻 Codex Developer Prompt — Refactor & Advance the Voice Assistant

**Mission:** Implement the refactoring plan in **small, verifiable sprints** without losing existing features (unless explicitly superseded). Keep latency low, quality high, and the repo clean (no duplicates, no dead code on the import path).

**Repository assumptions**

* Root contains `backend/`, `ws_server/`, `voice-assistant-apps/`, `gui/`, `archive/`, `tests/` or `testsuite/`.
* Current unified entrypoint is `ws_server/cli.py` (WebSocket) and a legacy `backend/ws-server/ws-server.py` still exists.
* Electron desktop app lives in `voice-assistant-apps/desktop`.

**Golden rules**

1. **No feature regressions.** Replace only when the new path fully covers the old behavior.
2. **Single source of truth.** One server entrypoint (`python -m ws_server.cli`). No mirror copies under `backend/ws-server/`.
3. **Idempotent changes.** Scripts and transforms can run repeatedly.
4. **Atomic PRs.** One sprint → one commit with a clear message and a short changelog.
5. **Tests first mindset.** Add/adjust tests alongside changes. Keep them fast and hermetic.
6. **Naming hygiene.** Use clear, descriptive names. Avoid `enhanced/advanced/pro/v2/ultimate`.
7. **Local only.** Do not call external services or invent APIs. Operate on the repo as it is.

---

## Kickoff (run first)

```bash
git checkout -b feat/refactor-foundation
python3 -m pip install -U pip
# if ruff/pytest/pytest-asyncio not present:
python3 -m pip install ruff pytest pytest-asyncio
```

Create a **refactor dashboard** file to track progress:

* `DEPRECATIONS.md` – list of files replaced/removed + new path.
* `docs/UNIFIED_SERVER.md` – how to run, protocol, env, health/metrics.
* `docs/REFACTOR_PLAN.md` – checklist of sprints below, keep in sync.

---

## Sprint 1 — Duplicate detection & quarantine

**Goal:** Identify and quarantine parallel implementations and backups so they **cannot** be imported inadvertently.

**Tasks**

* Add `scripts/repo_hygiene.py` to detect:

  * backup files: `*.bak*`, `*indentfix*`, `*fix*`
  * parallel servers: `backend/ws-server/ws-server.py`, `ws_server/transport/*enhanced*`, legacy copies in `archive/`
  * duplicated TTS engines (e.g., Zonos in multiple places)
* Move legacy/unused to `archive/` and add `pyproject.toml`/`setup.cfg` `exclude` patterns or runtime guards so **none** are on `sys.path`.
* Add a CI‑style check: `python scripts/repo_hygiene.py --check` exits non‑zero on violations.

**Acceptance**

* `repo_hygiene` finds 0 violations.
* `DEPRECATIONS.md` lists every quarantined path and the replacement.

**Commit message**

```
sprint-1(repo-hygiene): detect duplicates, quarantine legacy code, add DEPRECATIONS.md
```

---

## Sprint 2 — Single entrypoint & import path sanitation

**Goal:** One server entrypoint: `python -m ws_server.cli`. Desktop app must use this.

**Tasks**

* Ensure `voice-assistant-apps/desktop` spawns `python -m ws_server.cli` (not `backend/ws-server/ws-server.py`).
* In `ws_server/transport/server.py` add a **strict path gate** to prevent importing from `backend/ws-server/` unless explicitly needed for compatibility shims.
* Remove any dynamic legacy imports from hot paths; keep a minimal shim only if necessary and document in `DEPRECATIONS.md`.

**Acceptance**

* Desktop `npm start` logs show `ws_server.cli` entrypoint.
* No imports from `backend/ws-server/` at runtime.

**Commit message**

```
sprint-2(entrypoint): unify to ws_server.cli and harden import paths for legacy-free runtime
```

---

## Sprint 3 — Modular slicing of the monolith

**Goal:** Break legacy server logic into cohesive modules without behavior change.

**Tasks**

* Create (or complete) target layout under `ws_server/`:

  ```
  core/      (config, connections, streams)
  protocol/  (json_v1, binary_v2, handshake)
  transport/ (server, fastapi_adapter)
  metrics/   (collector, http_api, perf_monitor)
  tts/       (manager, engines/{piper,kokoro,zonos})
  routing/   (intent_router, skills loader)
  auth/      (token, rate_limit placeholder)
  ```
* Extract code into modules with same public interfaces used by `cli.py` / current handlers.

**Acceptance**

* `python -m ws_server.cli` runs with identical logs and behavior as before.

**Commit message**

```
sprint-3(modularity): extract server monolith into core/protocol/transport/metrics/routing/tts/auth
```

---

## Sprint 4 — Config consolidation & naming hygiene

**Goal:** One config source, consistent env usage, no magic literals.

**Tasks**

* `ws_server/core/config.py`: dataclass or pydantic settings loading `.env` + defaults.
* Replace scattered env reads with `Config`.
* Normalize names: `WS_HOST`, `WS_PORT`, `METRICS_PORT`, `STT_MODEL`, `STT_DEVICE`, `TTS_ENGINE`, `TTS_VOICE`, `JWT_SECRET`, etc.
* Remove suffixes in code identifiers; keep protocol names stable via `protocol/*`.

**Acceptance**

* `grep` shows no ad‑hoc `os.getenv(...)` in non‑config files.
* Docs updated with env table.

**Commit message**

```
sprint-4(config): centralize settings, normalize env names, update docs
```

---

## Sprint 5 — TTS single source of truth & lazy loading

**Goal:** Only one Zonos/Piper/Kokoro implementation; engines are lazy‑loaded, with graceful fallback.

**Tasks**

* Re‑export duplicates to a single canonical engine implementation (prefer `backend/tts/engine_zonos.py` or `ws_server/tts/engines/zonos.py` → pick one; the other becomes a thin re‑export or is removed).
* `TTSManager` supports lazy import; if engine unavailable, mark **unavailable** and auto‑fallback (Piper).

**Acceptance**

* When Zonos assets are missing, a warning is logged; Piper answers and system does not crash.

**Commit message**

```
sprint-5(tts): unify engine sources, add lazy loading and robust fallback
```

---

## Sprint 6 — STT in‑memory & streaming‑friendly

**Goal:** No temp files; ready for streaming STT.

**Tasks**

* Convert STT ingestion to in‑memory buffers (`bytes` → `np.int16`), remove WAV temp files and subprocesses.
* Keep current behavior and quality; add TODO stubs for true streaming.

**Acceptance**

* No file I/O in STT hot path; latency drops measurably on short utterances.

**Commit message**

```
sprint-6(stt): eliminate temp-file I/O; in-memory audio path for faster transcription
```

---

## Sprint 7 — Binary ingress + JSON compatibility

**Goal:** Unified transport that accepts JSON v1 and binary audio frames, negotiated in handshake.

**Tasks**

* `protocol/handshake.py`: accept `{"op":"hello"}` and legacy `{"type":"hello"}`; reply `{"op":"ready", "features": {...}}`.
* `protocol/binary_v2.py`: parser/builder for audio frames; route to STT pipeline.
* Keep JSON `audio_chunk` (Base64) as fallback.

**Acceptance**

* Integration test: JSON‑only client works; binary client streams PCM16 LE frames.

**Commit message**

```
sprint-7(protocol): handshake negotiation; add binary audio ingress alongside JSON v1
```

---

## Sprint 8 — Staged TTS UX (intro Piper, main Zonos)

**Goal:** Perceptibly lower TTFB with high‑quality follow‑up.

**Tasks**

* `_limit_and_chunk(text)` (≤500 chars; target 80–180 per chunk).
* `_tts_staged()`:

  * Stage A: short Piper intro (CPU) first.
  * Stage B: Zonos main chunks (GPU) in parallel; cap chunks (≤3) and per‑chunk timeout (e.g., 8–10s).
* New WS messages: `tts_chunk` and `tts_sequence_end`.

**Acceptance**

* Desktop client receives intro chunk within \~sub‑second, then main chunks; on Zonos timeout only intro is played and sequence ends.

**Commit message**

```
sprint-8(tts-staged): chunking + staged playback (Piper intro → Zonos main) with timeouts and sequence events
```

---

## Sprint 9 — Metrics unification

**Goal:** One metrics collector for connections, audio throughput, TTS/STT latencies, errors.

**Tasks**

* `metrics/collector.py`: counters, histograms (e.g., `tts_chunk_emitted_total`, `tts_sequence_timeout_total`, `stt_latency_ms`).
* `metrics/http_api.py`: `/metrics`, `/health`.

**Acceptance**

* `curl http://127.0.0.1:$METRICS_PORT/metrics` exposes new metrics; `/health` returns 200.

**Commit message**

```
sprint-9(metrics): unify collector + HTTP endpoints for health and Prometheus scraping
```

---

## Sprint 10 — Intent routing & skills completion

**Goal:** Make routing real: local skills, LLM (Flowise), automation (n8n).

**Tasks**

* `routing/intent_router.py`:

  * Simple classifier (rules or lightweight model).
  * Dispatch matrix: skill → local handler; knowledge → Flowise (if env set); automation → n8n.
* `skills/` loader with clean extension points.

**Acceptance**

* With env configured, intents reach Flowise/n8n; without, local paths still function.

**Commit message**

```
sprint-10(routing): functional intent router with skills plugin loader and optional Flowise/n8n paths
```

---

## Sprint 11 — Error handling & client resilience

**Goal:** Harden server and client interaction.

**Tasks**

* Server: catch/send structured errors, close sequences cleanly on failure, backpressure logs.
* Desktop: add reconnect with backoff; health probe on startup; error banner on auth/connect failures.

**Acceptance**

* Kill/restart server → client reconnects automatically; no orphaned sequences.

**Commit message**

```
sprint-11(hardening): structured errors, graceful sequence closes, desktop reconnect with backoff
```

---

## Sprint 12 — Model discovery & validation

**Goal:** Fewer surprises at runtime.

**Tasks**

* Voice alias map (e.g., `de-thorsten-low` → `de_DE-thorsten-low`) and model scanning at startup.
* CLI `python -m ws_server.cli --validate-models` prints missing/linked models.

**Acceptance**

* Startup logs list available voices; missing assets produce actionable warnings.

**Commit message**

```
sprint-12(models): voice aliasing, asset discovery, and validation CLI
```

---

## Sprint 13 — Configurable LLM prosody prompt

**Goal:** Consistently speakable output.

**Tasks**

* Add system prompt promoting short, punctuated sentences (≤500 chars).
* Server‑side hard cap post‑gen via `_limit_and_chunk`.

**Acceptance**

* Long LLM answers are neatly chunked and read well; no Markdown/list formatting.

**Commit message**

```
sprint-13(llm-prosody): add speakable system prompt and hard-cap chunking
```

---

## Sprint 14 — CI pipeline & “no duplicates” gate

**Goal:** Keep debt from creeping back.

**Tasks**

* GitHub Actions (or local script): `ruff`, `pytest -q`, `scripts/repo_hygiene.py --check`.
* Fail CI if hygiene fails or coverage drops below baseline (set minimal threshold initially).

**Acceptance**

* CI green locally; hygiene fails on re‑introduced backups/dupes.

**Commit message**

```
sprint-14(ci): add lint/tests/hygiene gates; fail on duplicates or deprecated paths
```

---

## Sprint 15 — Desktop playback sequencer polish

**Goal:** Smooth multi‑chunk audio UX.

**Tasks**

* Queue by `sequence_id`, prebuffer next chunk, crossfade 80–120 ms.
* Toggles: fast‑start (Piper), chunk playback, crossfade duration.

**Acceptance**

* No audible gaps between intro and main; UI shows chunk progress.

**Commit message**

```
sprint-15(desktop): queued playback with prebuffer and crossfade; UX toggles
```

---

## Sprint 16 — Docs & release notes

**Goal:** Ship a coherent story.

**Tasks**

* Update `docs/UNIFIED_SERVER.md`, `docs/STAGED_TTS.md`.
* Write `UPGRADE_NOTES.md` for the unified entrypoint.
* Summarize deprecations in `DEPRECATIONS.md`.

**Acceptance**

* Fresh checkout can run backend + desktop app using only documented steps.

**Commit message**

```
sprint-16(docs): unify docs, upgrade notes, and final deprecations list
```

---

## Test suite expectations (add or fix as you go)

* **Protocol/transport**

  * JSON hello + legacy `type:"hello"` accepted; `op:"ready"` returned.
  * Binary frames parsed and routed; JSON base64 fallback still works.
* **TTS/STT**

  * `_limit_and_chunk` unit tests: boundaries (120/180/500).
  * Staged TTS emits `tts_chunk` then `tts_sequence_end` even on Zonos timeout.
  * Engine fallback when model missing.
* **Routing**

  * Skill → local handler; knowledge → Flowise (mocked); automation → n8n (mocked).
* **Metrics/health**

  * `/health` 200; `/metrics` exports new counters/histograms.

---

## Done criteria (project level)

* One server entrypoint, **zero runtime imports** from legacy paths.
* No duplicates or backup files on the import path; hygiene script clean.
* Lower perceived TTFB via Piper intro; stable Zonos follow‑up.
* In‑memory STT with measurable latency improvement.
* Desktop app bound to unified server with reconnect.
* Clear docs; safe upgrade path; tests green.

---

**Final note to Codex:**
Operate only on files in this repository. Don’t fetch or invent external code. Keep each sprint self‑contained, reversible, and covered by tests and docs.

# Analyse der Projektstruktur und Refaktorierungsplan Sprachassistent
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
