# TODO Reduction Plan

## Prioritized Tasks

1. **ws_server/protocol/binary_v2.py** – verify PCM format and sample rate before processing. *Priority: High; Domain: WS-Server/Protocol*. Independent; ensures audio validity early.
2. **ws_server/stt/in_memory.py** – add streaming support without full buffering. *Priority: High; Domain: WS-Server/STT*. Independent; improves latency.
3. **ws_server/routing/skills.py** – flesh out skill interface and routing logic. *Priority: High; Domain: WS-Server/Routing*. Independent; needed for scalable skill system.
4. **ws_server/compat/legacy_ws_server.py** – stream chunk-wise and log Kokoro voice detection errors. *Priority: Medium; Domain: WS-Server/Compat*. Depends on task 2 to reuse streaming utilities.
5. **ws_server/metrics/collector.py** – track memory usage and network throughput. *Priority: Medium; Domain: WS-Server/Metrics*. Independent; adds observability.
6. **voice-assistant-apps/shared/core/VoiceAssistantCore.js & AudioStreamer.js** – consolidate duplicated streaming logic. *Priority: Medium; Domain: Frontend*. Grouped because of tight coupling; answers open question about merging modules.
7. **gui/enhanced-voice-assistant.js** – merge with shared core modules to avoid duplication. *Priority: Medium; Domain: Frontend*. Follows task 6 to reuse unified core.
8. **ws_server/tts/staged_tts/chunking.py** – review overlap with sanitizer/normalizer. *Priority: Medium; Domain: WS-Server/TTS*. Blocked by low-priority sanitizer unification tasks.

### Low Priority Tasks

- Backend TTS stubs and wrappers clean-up.
- FastAPI transport adapter.
- Text sanitizer/normalizer unification and related config alignment.
- Documentation updates and removal of legacy backups.
- Tools script error handling.

## Notes
- Tasks grouped to keep commits atomic and reviewable.
- Sanitizer/normalizer unification (low priority) must precede chunking review (task 8).
- Consolidation of VoiceAssistantCore and AudioStreamer (task 6) informs decision on GUI module (task 7).
