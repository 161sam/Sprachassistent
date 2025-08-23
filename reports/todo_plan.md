# TODO Work Plan

## Frontend
1. **Consolidate VoiceAssistantCore with AudioStreamer**
   - **Files:** `voice-assistant-apps/shared/core/VoiceAssistantCore.js`, `voice-assistant-apps/shared/core/AudioStreamer.js`
   - **Priority:** Medium
   - **Domain:** Frontend
   - **Dependencies:** None
   - **Rationale:** Remove duplicated WebSocket/token handling to centralize streaming logic.

2. **Unify GUI client with shared core modules**
   - **Files:** `gui/enhanced-voice-assistant.js`
   - **Priority:** Medium
   - **Domain:** Frontend
   - **Dependencies:** Task 1 to provide unified streaming interface
   - **Rationale:** Avoid duplication between GUI and shared core for easier maintenance.

3. **GUI layout and design refresh**
   - **Files:** `gui/` assets
   - **Priority:** Low
   - **Domain:** Frontend
   - **Dependencies:** Task 2 to ensure layout targets final components
   - **Rationale:** Improve visual structure and usability.

4. **GUI animations (matrix-rain, avatar pulse, message flash)**
   - **Files:** `gui/` assets
   - **Priority:** Low
   - **Domain:** Frontend
   - **Dependencies:** Task 3 for stable layout foundation
   - **Rationale:** Enhance visual feedback and engagement.

## Open Questions
- Are VoiceAssistantCore and AudioStreamer both needed or can they be fully merged?
- Is the legacy WS server still required, or can the compat layer be dropped?
- Is `gui/enhanced-voice-assistant.js` still required once the shared core is used?
