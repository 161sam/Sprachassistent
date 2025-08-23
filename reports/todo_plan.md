# TODO Work Plan

## Frontend
1. **Merge VoiceAssistantCore & AudioStreamer**
   - **Files:** `voice-assistant-apps/shared/core/VoiceAssistantCore.js`, `voice-assistant-apps/shared/core/AudioStreamer.js`
   - **Priority:** Medium
   - **Domain:** Frontend
   - **Dependencies:** none
   - **Rationale:** eliminate duplicate streaming logic and centralize audio handling.

2. **Consolidate GUI with shared core modules**
   - **Files:** `gui/enhanced-voice-assistant.js`
   - **Priority:** Medium
   - **Domain:** Frontend
   - **Dependencies:** Task 1 (shared streaming core ready)
   - **Rationale:** align GUI with unified core to reduce maintenance overhead.

3. **GUI layout and design refresh**
   - **Files:** `gui/` assets
   - **Priority:** Low
   - **Domain:** Frontend
   - **Dependencies:** Task 2 to avoid conflicts
   - **Rationale:** improve usability and visual structure.

4. **GUI animations (matrix-rain, avatar pulse, message flash)**
   - **Files:** `gui/` assets
   - **Priority:** Low
   - **Domain:** Frontend
   - **Dependencies:** Task 3 for finalized layout
   - **Rationale:** enhance visual feedback and user engagement.

## Backend
5. **Replace stubbed audio dependencies**
   - **Files:** `torch.py`, `torchaudio.py`, `soundfile.py`, `piper/__init__.py`
   - **Priority:** Low
   - **Domain:** Backend
   - **Dependencies:** availability of real libraries or scoped test mocks
   - **Rationale:** remove brittle stubs and rely on real packages or dedicated mocks.

## Open Questions
- Are VoiceAssistantCore and AudioStreamer both needed or can they be fully merged?
- Is the legacy WS server still required, or can the compat layer be dropped?
- Are the torch/torchaudio/soundfile stubs still necessary once real libraries are installed?
- Is `gui/enhanced-voice-assistant.js` still required or can its features be merged into the shared core modules?
- Is the archived legacy skill system (`archive/legacy_ws_server`) still required or can it be removed entirely?
