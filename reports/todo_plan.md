# TODO Plan

A prioritized roadmap derived from `TODO-Index.md`.
For each item we list file path, domain, priority, dependencies, and open questions.

## Medium Priority
1. **Merge streaming logic**  
   - **Files:** `voice-assistant-apps/shared/core/VoiceAssistantCore.js`, `voice-assistant-apps/shared/core/AudioStreamer.js`, `gui/enhanced-voice-assistant.js`  
   - **Domain:** Frontend  
   - **Deps:** clarify whether `VoiceAssistantCore` and `AudioStreamer` can be unified or one retired.  
   - **Open:** Are both modules needed or can functionality be merged?  

## Low Priority
1. **Real dependency modules**  
   - **Files:** `torch.py`, `torchaudio.py`, `soundfile.py`, `piper/__init__.py`  
   - **Domain:** Backend  
   - **Deps:** availability of actual libraries or creation of test mocks.  
   - **Open:** Are the stub modules still necessary once real libraries are installed?  
2. **FastAPI transport adapter**  
   - **File:** `ws_server/transport/fastapi_adapter.py`  
   - **Domain:** WS-Server  
   - **Deps:** none.  
3. **Unified text pipeline**  
   - **Files:** `ws_server/tts/text_sanitizer.py`, `ws_server/tts/text_normalize.py`  
   - **Domain:** WS-Server  
   - **Deps:** sanitizer should be unified before adding more TTS features.  
4. **Voice configuration single source**  
   - **Files:** `ws_server/tts/voice_aliases.py`, `config/tts.json`, `env.example`  
   - **Domain:** Config  
   - **Deps:** choose canonical config source.  
5. **GUI layout and design refresh**  
   - **Files:** `gui/*`  
   - **Domain:** Frontend  
   - **Deps:** none.  
6. **GUI animations**  
   - **Files:** `gui/*`  
   - **Domain:** Frontend  
   - **Deps:** depends on layout refresh.  
7. **Legacy skill cleanup** ✅ Done  
   - **Files:** `archive/legacy_ws_server/skills/`  
   - **Domain:** WS-Server  
   - **Deps:** confirm no active references.  

