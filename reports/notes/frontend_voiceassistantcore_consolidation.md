# voice-assistant-apps/shared/core/VoiceAssistantCore.js – consolidate with AudioStreamer

Duplicate `getAuthToken` logic exists in both VoiceAssistantCore and AudioStreamer.
Solution: move token retrieval into new `ws-utils.js` helper, import and use in core.
This reduces duplication and aligns with plan to unify streaming modules.
