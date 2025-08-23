# 📌 Zentrale TODO-Übersicht

## Backend
- **backend/tts/engine_zonos.py**: log voice directory scan errors instead of silent pass. _Prio: Niedrig_
- **backend/tts/engine_zonos.py**: log cleanup errors instead of silent pass. _Prio: Niedrig_
- **backend/tts/base_tts_engine.py**: raise `NotImplementedError` in abstract methods for clearer contracts. _Prio: Niedrig_
- **backend/tts/tts_manager.py**: replace `DummyTTSManager` fallback with dedicated mock or remove it. _Prio: Mittel_
- **ws_server/tts/engines/piper.py**: relocate implementation to `backend/tts` to keep engines centralized. _Prio: Niedrig_

## Frontend
- **voice-assistant-apps/shared/core/VoiceAssistantCore.js**: deduplicate streaming logic with `AudioStreamer.js`. _Prio: Mittel_
- **voice-assistant-apps/shared/core/AudioStreamer.js**: unify with `VoiceAssistantCore.js` to avoid duplicate streaming logic. _Prio: Mittel_

## WS-Server / Protokolle
- **ws_server/compat/legacy_ws_server.py**: legacy compatibility – log missing event loop, handle cleanup/close errors, and replace `DummyTTSManager` stub. _Prio: Mittel_
- **ws_server/compat/legacy_ws_server.py**: legacy compatibility – plan migration away from this layer once transport server is updated. _Prio: Niedrig_
- **ws_server/transport/fastapi_adapter.py**: add tests and consider merging into core transport server. _Prio: Niedrig_
- **ws_server/tts/staged_tts/chunking.py**: streamline integration with `text_sanitizer`/`text_normalize` to reduce pipeline complexity. _Prio: Mittel_

## Config
- **backend/tts/voice_aliases.py**: merge with `ws_server/tts/voice_aliases.py` to avoid configuration drift. _Prio: Mittel_
- **config/tts.json**: deduplicate voice_map keys `de-thorsten-low` and `de_DE-thorsten-low`. _Prio: Niedrig_

## Dokumentation
- **docs/Refaktorierungsplan.md**: flesh out true streaming section with concrete milestones. _Prio: Mittel_

## Tools & Scripts
- **debug_server_start.py**: log cleanup errors instead of bare pass. _Prio: Niedrig_

## ❓ Offene Fragen
- ❓ **ws_server/compat/legacy_ws_server.py**: is the embedded `DummyTTSManager` still needed or should a dedicated mock be used? _Prio: Niedrig_
- ❓ **backend/tts/tts_manager.py**: is `DummyTTSManager` sufficient as a fallback or should a proper mock be used? _Prio: Niedrig_

