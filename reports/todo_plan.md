# TODO Work Plan

## WS-Server / Backend
1. **Unify TTS sanitization pipeline**
   - **Files:** `ws_server/tts/text_sanitizer.py`, `ws_server/tts/text_normalize.py`
   - **Priority:** Low
   - **Dependencies:** none
   - **Rationale:** Provides single entry point for text cleanup before chunking and synthesis.

2. **Replace stubbed audio dependencies**
   - **Files:** `torch.py`, `torchaudio.py`, `soundfile.py`, `piper/__init__.py`
   - **Priority:** Low
   - **Dependencies:** Availability of real libraries or test mocks.
   - **Rationale:** Remove brittle stubs, enabling real audio processing and clearer tests.

3. **Implement FastAPI transport adapter**
   - **Files:** `ws_server/transport/fastapi_adapter.py`
   - **Priority:** Low
   - **Dependencies:** None
   - **Rationale:** Allow HTTP clients to reuse WS server logic via FastAPI.

## Frontend
4. **Merge VoiceAssistantCore & AudioStreamer**
   - **Files:** `voice-assistant-apps/shared/core/VoiceAssistantCore.js`, `voice-assistant-apps/shared/core/AudioStreamer.js`
   - **Priority:** Medium
   - **Dependencies:** None
   - **Rationale:** Avoid duplicated streaming code across clients.

5. **Consolidate GUI with shared core modules**
   - **Files:** `gui/enhanced-voice-assistant.js`
   - **Priority:** Medium
   - **Dependencies:** Task 4 (shared streaming core ready)
   - **Rationale:** Reduce duplication, align GUI with core logic.

6. **GUI layout and design refresh**
   - **Files:** `gui/` assets
   - **Priority:** Low
   - **Dependencies:** Task 5 to avoid merge conflicts
   - **Rationale:** Improve user experience.

7. **GUI animations (matrix-rain, avatar pulse)**
   - **Files:** `gui/` assets
   - **Priority:** Low
   - **Dependencies:** Task 6 for final layout
   - **Rationale:** Enhance visual feedback.

## Open Questions
- Are VoiceAssistantCore and AudioStreamer both needed or can they be merged?
- Is the legacy WS server still required, or can the compat layer be dropped?
- Are the torch/torchaudio/soundfile stubs still necessary once real libraries are installed?
- Is `gui/enhanced-voice-assistant.js` still required or can its features be merged into the shared core modules?
- Is the archived legacy skill system (`archive/legacy_ws_server`) still required or can it be removed entirely?
