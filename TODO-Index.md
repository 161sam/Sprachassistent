# 📌 Zentrale TODO-Übersicht

## Backend
- **backend/tts/engine_zonos.py**: log voice directory scan errors instead of silent pass. _Prio: Niedrig_
- **backend/tts/engine_zonos.py**: log cleanup errors instead of silent pass. _Prio: Niedrig_
- **backend/tts/base_tts_engine.py**: raise `NotImplementedError` in abstract methods for clearer contracts. _Prio: Niedrig_
- **backend/tts/tts_manager.py**: replace `DummyTTSManager` fallback with dedicated mock or remove it. _Prio: Mittel_
- **ws_server/tts/engines/piper.py**: relocate implementation to `backend/tts` to keep engines centralized. _Prio: Niedrig_
- **backend/tts/kokoro_tts_engine.py**: load voices from shared config to avoid duplication. _Prio: Niedrig_

## Frontend
- **voice-assistant-apps/shared/core/VoiceAssistantCore.js**: deduplicate streaming logic with `AudioStreamer.js`. _Prio: Mittel_
- **voice-assistant-apps/shared/core/AudioStreamer.js**: unify with `VoiceAssistantCore.js` to avoid duplicate streaming logic. _Prio: Mittel_

## WS-Server / Protokolle
- **ws_server/compat/legacy_ws_server.py**: legacy compatibility – log missing event loop, handle missing torch dependency, cleanup/close errors, and replace `DummyTTSManager` stub. _Prio: Mittel_
- **ws_server/compat/legacy_ws_server.py**: legacy compatibility – plan migration away from this layer once transport server is updated. _Prio: Niedrig_
- **ws_server/protocol/json_v1.py**: deprecate `json_v1` in favour of `binary_v2` to avoid protocol fragmentation. _Prio: Niedrig_
- **ws_server/transport/fastapi_adapter.py**: add tests and consider merging into core transport server. _Prio: Niedrig_
- **ws_server/tts/staged_tts/chunking.py**: streamline integration with `text_sanitizer`/`text_normalize` to reduce pipeline complexity. _Prio: Mittel_
- **ws_server/tts/text_sanitizer.py** & **ws_server/tts/text_normalize.py**: clarify and consolidate responsibilities to avoid overlapping sanitization steps. _Prio: Mittel_
- **ws_server/tts/staged_tts/staged_processor.py**: unify sanitizer and normalizer pipeline to reduce duplicate processing. _Prio: Mittel_

## Config
- **backend/tts/voice_aliases.py** & **ws_server/tts/voice_aliases.py**: merge to avoid configuration drift. _Prio: Mittel_
- **env.example**: deduplicate TTS defaults with `config/tts.json` to avoid confusion. _Prio: Niedrig_

## Dokumentation
- **docs/Refaktorierungsplan.md**: flesh out true streaming section with concrete milestones. _Prio: Mittel_

## Tools & Scripts
- **debug_server_start.py**: log cleanup errors instead of bare pass. _Prio: Niedrig_

## ❓ Offene Fragen
- ❓ **ws_server/compat/legacy_ws_server.py**: is the embedded `DummyTTSManager` still needed or should a dedicated mock be used? _Prio: Niedrig_
- ❓ **backend/tts/tts_manager.py**: is `DummyTTSManager` sufficient as a fallback or should a proper mock be used? _Prio: Niedrig_
- ❓ **docs/Code-und-Dokumentationsreview.md**: clarify whether `EnhancedVoiceAssistant.js` is still required or fully replaced by `VoiceAssistantCore`. _Prio: Niedrig_
- ❓ **ws_server/protocol/json_v1.py**: maintain JSON v1 protocol or migrate entirely to `binary_v2`? _Prio: Niedrig_
- ❓ **voice-assistant-apps/shared/workers/audio-streaming-worklet.js**: are multiple AudioWorklets necessary or can streaming be consolidated? _Prio: Niedrig_

