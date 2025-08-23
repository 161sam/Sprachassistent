# TODO Plan

## Overview
A prioritized list of open TODOs extracted from `TODO-Index.md` with dependencies and scope.

## High Priority
*(none pending)*

## Medium Priority
1. **Merge streaming logic** – consolidate `VoiceAssistantCore.js`, `AudioStreamer.js`, and `gui/enhanced-voice-assistant.js` to remove duplicate client streaming code. (Frontend)
   - Depends on resolving whether VoiceAssistantCore and AudioStreamer can be fully merged.

## Low Priority
1. **Real dependency modules** – replace stub modules `torch.py`, `torchaudio.py`, `soundfile.py`, and `piper/__init__.py` with real dependencies or test mocks. (Backend)
2. **FastAPI transport adapter** – implement `ws_server/transport/fastapi_adapter.py` to expose the server via FastAPI. (WS-Server)
3. **Unified text pipeline** – refine `ws_server/tts/text_sanitizer.py` and `text_normalize.py` into a coherent sanitizer/normalizer/chunking pipeline. (WS-Server)
4. **Legacy skill cleanup** – decide on `archive/legacy_ws_server/skills/__init__.py`: implement missing `BaseSkill` methods or remove module. (WS-Server)
5. **Voice configuration single source** – align `ws_server/tts/voice_aliases.py`, `config/tts.json`, and `.env` defaults. (Config)
6. **TTS config consolidation** – ensure `env.example` reflects defaults from `config/tts.json` to prevent drift. (Config)
7. **Documentation updates** – `docs/Refaktorierungsplan.md` needs TODO stubs for true streaming; `docs/GUI-TODO.md` tasks should be merged into the central roadmap. (Docs)

## Dependency Map
- Voice configuration tasks (5 & 6) depend on the decision of a single canonical config source.
- Unified text pipeline (3) should precede any further TTS feature work.
- Legacy skill cleanup (4) can proceed independently after confirming no active references.

