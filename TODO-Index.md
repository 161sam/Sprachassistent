# 📌 Zentrale TODO-Übersicht

## Backend
- **backend/tts/piper_tts_engine.py**: remove deprecated wrapper for Piper engine. _Prio: Niedrig_

## Frontend
- **voice-assistant-apps/shared/core/VoiceAssistantCore.js**: consolidate with AudioStreamer to avoid duplicate streaming logic. _Prio: Mittel_
- **voice-assistant-apps/shared/core/AudioStreamer.js**: merge with VoiceAssistantCore for shared streaming logic. _Prio: Mittel_

## WS-Server / Protokolle
- **ws_server/stt/in_memory.py**: implement streaming support without buffering entire audio. _Prio: Hoch_
- **ws_server/compat/legacy_ws_server.py**: stream chunk-wise without buffering entire audio. _Prio: Mittel_
- **ws_server/routing/skills.py**: flesh out skill interface and routing logic. _Prio: Hoch_
- **ws_server/transport/fastapi_adapter.py**: implement FastAPI transport adapter. _Prio: Niedrig_
- **ws_server/tts/text_sanitizer.py**: unify sanitizer, normalizer and chunking pipeline. _Prio: Niedrig_

## Config
- **ws_server/tts/voice_aliases.py**: unify voice alias config with `config/tts.json` and environment. _Prio: Niedrig_
- **config/tts.json**: align with `voice_aliases.py` to remove duplication. _Prio: Niedrig_

## Dokumentation
- **docs/Refaktorierungsplan.md**: add TODO stubs for true streaming. _Prio: Niedrig_

## ❓ Offene Fragen
- ❓ Are VoiceAssistantCore and AudioStreamer both needed or can they be merged?
- ❓ Is the legacy WS server still required, or can the compat layer be dropped?
