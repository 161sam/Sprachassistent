Perfekt, ich habe deine `AGENTS.md` in sauberes, durchgängiges **Englisch** übertragen und gleichzeitig sprachlich verbessert, sodass sie für Entwickler\*innen und Codex-Agenten optimal nutzbar ist:

# AGENTS – Project Guide for AI Assistants

## Project Overview  
**Sprachassistent** is a modular, privacy-first voice assistant platform with a local backend (Raspberry Pi/Odroid hardware) and cross-platform client apps.  
It performs **speech recognition (STT)** and **speech synthesis (TTS)** entirely on-device, without relying on external cloud services.  

The system can intelligently route user commands to:  
- Built-in **local skills**  
- An integrated **LLM agent**  
- External **automation workflows (n8n)**  

Client applications (Electron Desktop, Android Cordova, Web GUI) connect to the backend via **WebSockets**, streaming audio in and receiving text/audio responses in real time.

---

## Architecture & Core Components  
- **Speech-to-Text (STT):** Faster-Whisper (CTranslate2 Whisper model), running locally.  
- **Text-to-Speech (TTS):** Multiple engines supported: **Zonos** (default), **Piper**, **Kokoro**. Switching at runtime is possible.  
- **Intent Routing:**  
  - Local **skills** → handled by plugin.  
  - General queries → routed to the **LLM agent** (via Flowise).  
  - Automation requests → passed to **n8n workflows**.  
- **LLM Agent Integration:** Flowise AI flows orchestrate reasoning and query handling.  
- **Automation Workflows:** n8n automates tasks such as smart home control and third-party integrations.  
- **Client Interfaces:** Electron desktop, Cordova mobile, and Web GUI (audio capture and playback).  

---

## Setup & Usage  
1. **Install Dependencies:**  
   ```bash
   pip install -r requirements.txt
   cd voice-assistant-apps && npm install
   ```


2. **Configuration:**

   * Copy `.env.example` → `.env`
   * Important variables: `WS_HOST`, `WS_PORT`, `STT_MODEL`, `STT_DEVICE`, `TTS_ENGINE`
   * Default values provided in `.env.defaults`

3. **Run Backend:**

   ```bash
   python -m ws_server.cli
   ```

4. **Run Desktop App:**

   ```bash
   cd voice-assistant-apps/desktop && npm start
   ```

---

## Naming & File Hygiene

* Use **clear, precise names** (avoid `enhanced`, `v2`, `pro`, etc.).
* Always check whether existing code can be extended before creating new files.
* Obsolete/replaced files → move to `archive/` and document in `DEPRECATIONS.md`.
* Ensure consistency across function names, module names, and file structure.

---

# 🧑‍💻 Codex Developer Prompt: Unified WS-Server + Staged-TTS

## Objective

Codex should:

1. Review, improve, and extend all previous sprints.
2. Implement the new sprints (7–16).
3. Apply changes in **small, atomic commits per sprint**.
4. Maintain tests, logs, documentation, and repository hygiene.

---

## Main Goal: Staged-TTS & UX Improvement

### Concept

* **Two-stage TTS pipeline:**

  * Stage A: short **Piper intro** (CPU, immediate feedback).
  * Stage B: parallel **Zonos main chunks** (GPU, detailed output).
* **Chunking:** limit ≤500 characters total, 80–180 per chunk.
* **LLM system prompt:** natural, spoken sentences; no Markdown or lists.
* **Client playback:** sequence `[INTRO(piper)] → [MAIN(zonos)…]` with 80–120 ms crossfade.
* **Fallbacks:** if Zonos fails or stalls, Piper output alone is delivered.

---

## Sprints to Implement

### Sprint 1 — Binary Ingress

* Extend WebSocket transport: JSON handshake + binary frames (OpCode 2).
* Message structure: `type`, `op`, `payload`, `sequence_id`.
* Audio streaming format: PCM16 LE.

### Sprint 2 — Staged-TTS Pipeline

* Implement `_limit_and_chunk(text)` (≤500 chars, 80–180 per chunk).
* Implement `_tts_staged()`: Piper intro + Zonos in parallel.
* Add WebSocket events: `tts_chunk`, `tts_sequence_end`.
* Add Zonos timeout (8–10 s per chunk).

### Sprint 3 — Metrics Collector

* Add Prometheus metrics:

  * `tts_chunk_emitted_total`
  * `tts_sequence_timeout_total`
  * `tts_engine_unavailable_total`
* Expose endpoint `/metrics`.

### Sprint 4 — Cleanup: Backups & Duplicates

* Move `.bak`, `_fix`, `_indentfix`, legacy servers → `archive/`.
* Maintain `DEPRECATIONS.md` (mapping old → new).
* Only `ws_server/` remains as the active codebase.

### Sprint 5 — Integration Tests

* Smoke tests: handshake, ping/pong, full TTS sequence.
* Unit tests: `_limit_and_chunk()`, `_tts_staged()` with dummy engines.

### Sprint 6 — CI Workflow

* GitHub Actions:

  * `pytest -q`
  * `scripts/repo_hygiene.py --check`
  * `ruff` lint (`ws_server/**`, `backend/tts/**`).

### Sprint 7 — Desktop/Electron Integration

* Ensure Electron app launches `python -m ws_server.cli`.
* Pass `.env` variables through (`WS_HOST`, `WS_PORT`, `JWT`, etc.).
* Add `/health` check; show error dialog if server not reachable.

### Sprint 8 — TTS Model Discovery & Voice Aliases

* Implement alias map (e.g., `'de-thorsten-low': 'de_DE-thorsten-low'`).
* Log all discovered models.
* Zonos: optional registration → mark as unavailable instead of crashing.
* Auto-fallback: Piper if Zonos is missing.

### Sprint 9 — Staged-TTS Fail-Safety

* Always attempt Piper intro.
* On Zonos error/timeout: return Piper only, plus `tts_sequence_end`.

### Sprint 10 — Repo Hygiene & Structure

* `scripts/repo_hygiene.py` detects duplicates and moves them to `archive/`.
* Maintain single server source: `ws_server/`.
* `DEPRECATIONS.md` lists all replaced files.

### Sprint 11 — CI Check “No Duplicates”

* CI fails if `.bak` files, duplicates, or old server mirrors are found.

### Sprint 12 — Desktop Client Playback Sequencer

* Implement queue for `tts_chunk`/`tts_sequence_end`.
* Add pre-buffering + 80–120 ms crossfade.
* UI toggles: quickstart Piper, chunked playback, crossfade duration.

### Sprint 13 — LLM Prosody Prompt

* System prompt: ≤500 chars, natural speech style, no lists/Markdown.
* Enforced via `_limit_and_chunk()`.

### Sprint 14 — Model Asset Validation

* On startup: check `.onnx` + `.onnx.json` presence.
* Warn + suggest fix if broken symlinks.
* CLI flag `--validate-models` lists available voices & aliases.

### Sprint 15 — Config Consolidation

* Centralize defaults in `core/config.py`.
* Electron launcher loads `.env`, no separate JS defaults.
* `config/tts.json` only contains user overrides.

### Sprint 16 — Documentation & Release Notes

* Add `docs/UNIFIED_SERVER.md`: entrypoint, events, settings.
* Add `docs/STAGED_TTS.md`: timeouts, fallbacks, UX notes.
* Release notes:

  * **Breaking:** unified entrypoint
  * **Deprecated:** legacy server files
  * **New:** voice aliasing & model validation

---

## Guidelines for Codex

* **Commits:** one per sprint, message format `sprint-N: …`.
* **Idempotency:** patches must be safe to apply multiple times.
* **Logs:** in German, concise and clear.
* **Tests:** write failing test first, then fix.
* **No monkey-patches**; prefer clean integration and refactoring.

---
