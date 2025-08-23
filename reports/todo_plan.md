# TODO Work Plan

This plan summarizes remaining TODOs from `TODO-Index.md`, ordered by priority and grouped by domain. High priority items are none; medium items first, then low.

## Medium Priority
1. **Merge streaming logic (Frontend)**  
   - Files: `voice-assistant-apps/shared/core/VoiceAssistantCore.js`, `voice-assistant-apps/shared/core/AudioStreamer.js`, `gui/enhanced-voice-assistant.js`  
   - Goal: consolidate duplicated audio streaming code.  
   - Dependencies: clarify if both modules are still required (see open question).  
   - Blockers: pending decision on whether to merge or keep separate modules.

## Low Priority
1. **Remove legacy WS backup file**  
   - File: `ws_server/compat/legacy_ws_server.py.backup.int_fix`  
   - Goal: delete outdated backup file now that changes reside in `legacy_ws_server.py`.  
   - Dependencies: none; verify no unique code remains.
2. **Voice alias configuration unification**  
   - Files: `ws_server/tts/voice_aliases.py`, `config/tts.json`, `env.example`  
   - Goal: maintain a single source of truth for TTS voice aliases and defaults.  
   - Dependencies: need agreement on canonical config location.
3. **Cleanup stub modules**  
   - Files: `torch.py`, `torchaudio.py`, `soundfile.py`, `piper/__init__.py`  
   - Goal: replace temporary stubs with real dependencies or proper mocks.  
   - Dependencies: availability of required packages in environment.
4. **Backend TTS wrappers**  
   - Files: `backend/tts/piper_tts_engine.py`, `ws_server/tts/engines/piper.py`, `backend/tts/engine_zonos.py`  
   - Goal: remove deprecated wrappers and replace silent exception blocks with explicit error handling.  
   - Dependencies: ensure new implementations cover previous behaviour.
5. **Text sanitizer and normalizer refactor**  
   - Files: `ws_server/tts/text_sanitizer.py`, `ws_server/tts/text_normalize.py`  
   - Goal: unify responsibilities and integrate with existing chunking pipeline.  
   - Dependencies: rely on outcome of chunking pipeline review already completed.
6. **FastAPI transport adapter**  
   - File: `ws_server/transport/fastapi_adapter.py`  
   - Goal: implement FastAPI adapter to expose WebSocket server via FastAPI.  
   - Dependencies: none noted.
7. **Legacy skill module cleanup**  
   - File: `archive/legacy_ws_server/skills/__init__.py`  
   - Goal: implement `BaseSkill` methods or remove the archived module.  
   - Dependencies: decision on whether archived server remains required.
8. **Documentation updates**  
   - Files: `docs/Refaktorierungsplan.md`, `docs/GUI-TODO.md`  
   - Goal: add streaming TODOs and consolidate GUI tasks into central roadmap.  
   - Dependencies: none.

## Open Questions
- Are `VoiceAssistantCore` and `AudioStreamer` both needed or can they be merged?
- Is the legacy WS server still required, or can the compat layer be dropped?
- Are the torch/torchaudio/soundfile stubs still necessary once real libraries are installed?
- Is `gui/enhanced-voice-assistant.js` still required or can its features be merged into the shared core modules?
- Can `ws_server/compat/legacy_ws_server.py.backup.int_fix` be removed after verifying no changes are needed?
- Is the archived legacy skill system (`archive/legacy_ws_server`) still required or can it be removed entirely?

