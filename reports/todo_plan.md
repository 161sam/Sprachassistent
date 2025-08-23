# TODO Work Plan

## Frontend
1. **Unify GUI client with shared core modules**
   - **Files:** `gui/enhanced-voice-assistant.js`, `gui/index.html`, `gui/app.js`
   - **Priority:** Medium
   - **Domain:** Frontend
   - **Dependencies:** None
   - **Rationale:** Avoid duplication by loading shared core modules directly.

2. **GUI layout and design refresh**
   - **Files:** `gui/` assets
   - **Priority:** Low
   - **Domain:** Frontend
   - **Dependencies:** Task 1 provides stable base
   - **Rationale:** Improve visual structure and usability.

3. **GUI animations (matrix-rain, avatar pulse, message flash)**
   - **Files:** `gui/` assets
   - **Priority:** Low
   - **Domain:** Frontend
   - **Dependencies:** Task 2 finalizes layout foundation
   - **Rationale:** Enhance visual feedback and engagement.

## Open Questions
- Are VoiceAssistantCore and AudioStreamer both needed or can they be fully merged?
- Is the legacy WS server still required, or can the compat layer be dropped?
- Is `gui/enhanced-voice-assistant.js` still required once the shared core is used?
