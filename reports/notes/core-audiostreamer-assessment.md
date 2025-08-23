# VoiceAssistantCore vs AudioStreamer

## Context
Both modules reside under `voice-assistant-apps/shared/core/`. `VoiceAssistantCore` orchestrates UI state, connection handling and metrics. `AudioStreamer` focuses on low-level WebSocket audio streaming and playback.

## Decision
Modules serve distinct purposes and should remain separate. `VoiceAssistantCore` may delegate streaming to `AudioStreamer`, avoiding duplication.

## Follow-up
- Ensure integration between the classes stays documented.
- Future refactor could expose a unified facade if duplication reappears.
