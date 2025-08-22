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

Codex should continuously maintain and refine the codebase:

1. Review, improve, and extend existing features.
2. Apply changes in **small, atomic commits**.
3. Maintain tests, logs, documentation, and repository hygiene.

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

## Maintenance Plan

Focus areas identified during repository analysis:

1. **Expand Test Coverage:** add dedicated unit tests for text chunking and intro creation.
2. **Metrics Enhancements:** track memory usage and network throughput in the metrics collector.
3. **Binary Audio Validation:** verify PCM format and sample rate in `binary_v2` before processing.
4. **Configurable Prompts:** allow loading the LLM system prompt from configuration for localization.
5. **TTS Crossfade:** make crossfade duration configurable for better UX experiments.

## Guidelines for Codex

* **Commits:** use clear, descriptive messages.
* **Idempotency:** patches must be safe to apply multiple times.
* **Logs:** in German, concise and clear.
* **Tests:** write failing test first, then fix.
* **No monkey-patches**; prefer clean integration and refactoring.

---
