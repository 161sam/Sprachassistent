# TODO Work Plan

This plan summarizes outstanding TODO items from `TODO-Index.md` with priorities and dependencies. Tasks are ordered high → low priority. Domains denote subsystem.

## High Priority
1. **ws_server/routing/skills.py** – flesh out `BaseSkill` interface and improve routing logic.
   - Domain: WS‑Server/Routing
   - Dependencies: none

## Medium Priority
1. **voice-assistant-apps/shared/core/VoiceAssistantCore.js** & **AudioStreamer.js** – consolidate streaming logic into a single module.
   - Domain: Frontend
   - Dependencies: mutual; consolidation required before GUI tasks
2. **gui/enhanced-voice-assistant.js** – remove duplication after core consolidation.
   - Domain: Frontend
   - Dependencies: depends on completion of the above consolidation
3. **ws_server/compat/legacy_ws_server.py** – stream chunk-wise without buffering and log Kokoro voice detection errors.
   - Domain: WS‑Server/Compat
   - Dependencies: decision on legacy server retention
4. **ws_server/tts/staged_tts/chunking.py** – review overlap with sanitizer/normalizer for unified pipeline.
   - Domain: WS‑Server/TTS
   - Dependencies: blocked until sanitizer/normalizer unification is defined
5. **ws_server/metrics/collector.py** – record memory usage and network throughput.
   - Domain: Metrics
   - Dependencies: none

## Low Priority
1. Backend cleanup (`backend/tts/piper_tts_engine.py`, `ws_server/tts/engines/piper.py`, `torch.py`/`torchaudio.py`/`soundfile.py`, `piper/__init__.py`, `backend/tts/engine_zonos.py`).
   - Domain: Backend
   - Dependencies: installation of real libraries
2. Config unification (`ws_server/tts/voice_aliases.py`, `config/tts.json`, `env.example`).
   - Domain: Config
   - Dependencies: coordinated update across all files
3. Documentation tasks (`docs/Refaktorierungsplan.md`, `docs/GUI-TODO.md`).
   - Domain: Documentation
   - Dependencies: none
4. Additional WS-Server tasks (FastAPI adapter, sanitizer unification, text_normalize clarification, staged TTS crossfade config, removal of backups and legacy skills).
   - Domain: WS‑Server
   - Dependencies: various; crossfade config depends on staged TTS pipeline decisions
5. Tooling (`start_voice_assistant.py` error handling).
   - Domain: Tools & Scripts
   - Dependencies: none

## Dependency Notes
- Sanitizer/normalizer unification must precede work on chunking overlap and text_normalize responsibilities.
- Merging `VoiceAssistantCore` and `AudioStreamer` is required before deduplicating the GUI module.
- Config consolidation across `voice_aliases.py`, `config/tts.json`, and `env.example` should be coordinated to avoid drift.

## Planned Execution Order
1. Implement skill interface and routing improvements (`ws_server/routing/skills.py`).
2. Consolidate frontend streaming modules and adjust GUI.
3. Improve legacy WS server and metrics collector.
4. Tackle backend cleanup and config/documentation tasks.
