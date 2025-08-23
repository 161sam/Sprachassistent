# TODO Plan

## Overview
This plan lists TODOs from `TODO-Index.md` ordered by priority and grouped by domain. Dependencies between tasks are noted to help schedule work.

## High Priority
1. **ws_server/stt/in_memory.py** – implement streaming support without buffering entire audio. Domain: WS-Server/STT. No blockers.
2. **ws_server/routing/skills.py** – flesh out skill interface and routing logic. Domain: WS-Server/Routing. Requires decisions on skill interface design.
3. **ws_server/protocol/binary_v2.py** – PCM format and sample rate validation. Already completed.

## Medium Priority
1. **voice-assistant-apps/shared/core/VoiceAssistantCore.js** & **AudioStreamer.js** – consolidate shared streaming logic. Domain: Frontend. Interdependent: merge logic between modules.
2. **gui/enhanced-voice-assistant.js** – consolidate with shared core modules after the above merge.
3. **ws_server/compat/legacy_ws_server.py** – stream chunk-wise without buffering; log Kokoro voice detection errors. Depends on clarifying need for legacy server.
4. **ws_server/tts/staged_tts/chunking.py** – review overlap with sanitizer/normalizer for unified pipeline. Blocked by sanitizer unification.
5. **ws_server/metrics/collector.py** – track memory usage and network throughput.

## Low Priority
1. Backend cleanup (piper engine wrapper, real dependencies for torch/torchaudio/soundfile, stub replacements).
2. Config consolidation (`voice_aliases.py`, `config/tts.json`, `env.example`).
3. Documentation updates (`docs/Refaktorierungsplan.md`, `docs/GUI-TODO.md`).
4. Additional WS-Server items (FastAPI adapter, text sanitizer unification, text_normalize responsibilities, staged TTS crossfade config, removal of backups/legacy skills).
5. Tools & scripts error handling (`start_voice_assistant.py`).

## Dependency Map
- Unifying sanitizer (`ws_server/tts/text_sanitizer.py`) precedes reviewing chunking overlap (`ws_server/tts/staged_tts/chunking.py`) and clarifying responsibilities (`ws_server/tts/text_normalize.py`).
- Merging `VoiceAssistantCore` and `AudioStreamer` is a prerequisite before de-duplicating `gui/enhanced-voice-assistant.js`.
- Config consolidation across `voice_aliases.py`, `config/tts.json`, and `env.example` should happen together to avoid drift.

## Planned Execution Order
1. Implement streaming STT in `ws_server/stt/in_memory.py`.
2. Define skill interface in `ws_server/routing/skills.py`.
3. Consolidate frontend streaming modules (`VoiceAssistantCore`, `AudioStreamer`, GUI).
4. Address legacy WS server improvements and metrics collector.
5. Progress through low priority cleanup and documentation tasks.

