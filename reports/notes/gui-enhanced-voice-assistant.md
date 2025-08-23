# Design Note: GUI uses shared core modules

## Context
`gui/enhanced-voice-assistant.js` duplicated logic from `voice-assistant-apps/shared/core`.

## Proposal
- Remove the standalone file.
- Load `AudioStreamer.js` and `VoiceAssistantCore.js` via script tags in `gui/index.html`.
- Update `gui/app.js` to instantiate `VoiceAssistantCore`.

## Rationale
Unifies WebSocket/audio streaming logic and keeps GUI in sync with shared modules.
