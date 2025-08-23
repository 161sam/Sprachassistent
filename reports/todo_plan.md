# TODO Work Plan

## Overview
Prioritized plan derived from TODO-Index.md. High priorities already completed; remaining tasks are Medium or Low. Tasks grouped by domain with dependencies.

## Medium Priority
1. **Consolidate streaming logic**  
   - Files: `voice-assistant-apps/shared/core/VoiceAssistantCore.js`, `voice-assistant-apps/shared/core/AudioStreamer.js`, `gui/enhanced-voice-assistant.js`  
   - Domain: Frontend  
   - Description: Merge duplicated audio streaming and WebSocket handling across these modules.  
   - Dependencies: Requires agreement on single source of truth for streaming API. Blocked by open question whether both Core and AudioStreamer are needed.

## Low Priority
2. **Remove deprecated Piper wrapper**  
   - File: `backend/tts/piper_tts_engine.py`  
   - Domain: Backend  
   - Description: Delete legacy wrapper once piper engine migrated.

3. **Sync WS Piper engine and handle sample‑rate errors**  
   - File: `ws_server/tts/engines/piper.py`  
   - Domain: Backend/WS  
   - Description: Keep parity with backend wrapper; raise explicit errors when sample rate read fails.

4. **Replace torch/torchaudio/soundfile stubs**  
   - Files: `torch.py`, `torchaudio.py`, `soundfile.py`, `piper/__init__.py`  
   - Domain: Backend/Tools  
   - Description: Use real dependencies or dedicated test mocks.

5. **Explicit error handling in Zonos TTS engine**  
   - File: `backend/tts/engine_zonos.py`  
   - Domain: Backend  
   - Description: Log sanitizer import failures and invalid speed conditioning instead of silent pass.

6. **FastAPI transport adapter**  
   - File: `ws_server/transport/fastapi_adapter.py`  
   - Domain: WS-Server  
   - Description: Implement adapter to expose WebSocket server via FastAPI.

7. **Unify text sanitizing pipeline**  
   - Files: `ws_server/tts/text_sanitizer.py`, `ws_server/tts/text_normalize.py`, `ws_server/tts/staged_tts/chunking.py`  
   - Domain: WS-Server  
   - Description: Ensure sanitizer, normalizer and chunking share a single pipeline.

8. **Config consistency for TTS voices**  
   - Files: `ws_server/tts/voice_aliases.py`, `config/tts.json`, `env.example`  
   - Domain: Config  
   - Description: Derive voice aliases from config and environment to avoid duplication.

9. **Documentation cleanup**  
   - Files: `docs/Refaktorierungsplan.md`, `docs/GUI-TODO.md`  
   - Domain: Docs  
   - Description: Add streaming TODO stubs and merge GUI tasks into central roadmap.

## Notes
- Open questions from TODO-Index remain regarding module consolidation, legacy server removal, and stub dependencies. These require further clarification before implementation.

## This iteration
- Completed tasks 2 and 3 (Piper wrapper removal and sample-rate error handling).
