# TODO Work Plan

This plan consolidates outstanding items from `TODO-Index.md`. Tasks are ordered by priority and grouped by domain. Dependencies describe prerequisite work.

## High Priority
*No open high‑priority TODOs – previously completed tasks include STT streaming, skill routing, and PCM validation.*

## Medium Priority
1. **Consolidate frontend streaming modules** – merge `voice-assistant-apps/shared/core/VoiceAssistantCore.js` and `AudioStreamer.js` to remove duplicated logic.
   - Domain: Frontend
   - Dependencies: none
2. **Deduplicate GUI helper** – adjust `gui/enhanced-voice-assistant.js` after core consolidation.
   - Domain: Frontend
   - Dependencies: depends on consolidation above
3. **Improve legacy WebSocket server** – stream chunk-wise and log Kokoro voice detection errors in `ws_server/compat/legacy_ws_server.py`.
   - Domain: WS‑Server / Compat
   - Dependencies: decision whether legacy server remains supported
4. **Unify TTS pipeline pieces** – review overlap in `ws_server/tts/staged_tts/chunking.py` once sanitizer and normalizer responsibilities are clarified.
   - Domain: WS‑Server / TTS
   - Dependencies: outcome of sanitizer/normalizer unification
5. **Extend metrics collector** – track system memory usage and network throughput in `ws_server/metrics/collector.py`.
   - Domain: Metrics
   - Dependencies: none

## Low Priority
1. **Backend cleanup** – remove deprecated wrappers and stubs (`backend/tts/piper_tts_engine.py`, `ws_server/tts/engines/piper.py`, `torch.py`, `torchaudio.py`, `soundfile.py`, `piper/__init__.py`, `backend/tts/engine_zonos.py`).
   - Domain: Backend
   - Dependencies: installing real libraries
2. **Config unification** – align `ws_server/tts/voice_aliases.py`, `config/tts.json`, and `.env.example`.
   - Domain: Config
   - Dependencies: coordinated update across files
3. **Documentation upkeep** – update `docs/Refaktorierungsplan.md` and `docs/GUI-TODO.md`.
   - Domain: Docs
   - Dependencies: none
4. **WS‑Server enhancements** – FastAPI adapter, sanitizer/normalizer clarification, staged TTS crossfade config, and removal of legacy backups.
   - Domain: WS‑Server
   - Dependencies: various; crossfade config depends on staged TTS design decisions
5. **Tooling improvements** – replace silent pass blocks in `start_voice_assistant.py` with explicit error handling.
   - Domain: Tools & Scripts
   - Dependencies: none

## Dependency Notes
- Sanitizer/normalizer unification must precede TTS chunking review.
- Merging `VoiceAssistantCore` and `AudioStreamer` is required before removing GUI duplication.
- Config files should be updated in lockstep to avoid drift.
