# TODO Work Plan

## WS-Server
1. **Clarify need for legacy compat layer**
   - **Files:** `ws_server/compat/legacy_ws_server.py`, `ws_server/transport/server.py`
   - **Priority:** High
   - **Domain:** Backend / WS
   - **Dependencies:** None
   - **Rationale:** Determine if `legacy_ws_server` remains necessary or can be removed.

## Frontend
1. **Assess merging of VoiceAssistantCore and AudioStreamer**
   - **Files:** `voice-assistant-apps/shared/core/VoiceAssistantCore.js`, `voice-assistant-apps/shared/core/AudioStreamer.js`
   - **Priority:** Medium
   - **Domain:** Frontend
   - **Dependencies:** None
   - **Rationale:** Decide if streaming logic can be unified or modules kept separate.

## Notes
All other TODO entries in `TODO-Index.md` are already marked as completed.
