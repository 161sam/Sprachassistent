# TODO Plan

## Overview
A prioritized list of open TODOs extracted from `TODO-Index.md` with dependencies and scope.

## High Priority
*(none pending)*

## Medium Priority
1. **Merge streaming logic** – consolidate `VoiceAssistantCore.js`, `AudioStreamer.js`, and `gui/enhanced-voice-assistant.js` to remove duplicate client streaming code. (Frontend)
   - Depends on clarifying whether `VoiceAssistantCore` and `AudioStreamer` can be fully merged.

## Low Priority
1. **Real dependency modules** – replace stub modules `torch.py`, `torchaudio.py`, `soundfile.py`, and `piper/__init__.py` with real dependencies or test mocks. (Backend)
2. **FastAPI transport adapter** – implement `ws_server/transport/fastapi_adapter.py` to expose the server via FastAPI. (WS-Server)
3. **Unified text pipeline** – refine `ws_server/tts/text_sanitizer.py` and `text_normalize.py` into a coherent sanitizer/normalizer/chunking pipeline. (WS-Server)
4. **Legacy skill cleanup** – decide on `archive/legacy_ws_server/skills/__init__.py`: implement missing `BaseSkill` methods or remove module. (WS-Server)
5. **Voice configuration single source** – align `ws_server/tts/voice_aliases.py`, `config/tts.json`, and `.env` defaults. (Config)
6. **TTS config consolidation** – ensure `env.example` reflects defaults from `config/tts.json` to prevent drift. (Config)
7. **GUI layout and design refresh** – reorganize GUI elements and update button/icon styling. (Frontend)
   - Animations depend on this layout work.
8. **GUI animations** – implement matrix-rain response animation and auxiliary effects like avatar pulse or message flash. (Frontend)

## Dependency Map
- Voice configuration tasks (5 & 6) depend on selecting a single canonical configuration source.
- Unified text pipeline (3) should precede additional TTS features.
- GUI animations (8) depend on the GUI layout and design refresh (7).
- Legacy skill cleanup (4) can proceed independently after confirming no active references.
