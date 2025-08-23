# 📌 Zentrale TODO-Übersicht

## Backend
- **backend/tts/piper_tts_engine.py**: remove deprecated wrapper for Piper engine. ✅ Done in commit `remove piper wrapper`. _Prio: Niedrig_
- **ws_server/tts/engines/piper.py**: handle sample rate read errors explicitly; backend wrapper removed. ✅ Done in commit `piper sample rate errors`. _Prio: Niedrig_
- **torch.py / torchaudio.py / soundfile.py**: replace stub modules with real dependencies or dedicated mocks. ✅ Done in commit `remove audio stubs`. _Prio: Niedrig_
- **piper/__init__.py**: replace stub with real piper dependency. ✅ Done in commit `remove audio stubs`. _Prio: Niedrig_
- **backend/tts/engine_zonos.py**: replace silent exception passes with explicit error handling for sanitizer import and speed conditioning. ✅ Done in commit `zonos error handling`. _Prio: Niedrig_

## Frontend
- **voice-assistant-apps/shared/core/VoiceAssistantCore.js**: consolidate with AudioStreamer to avoid duplicate streaming logic. ✅ Done in commit `shared ws utils`. _Prio: Mittel_
- **voice-assistant-apps/shared/core/AudioStreamer.js**: merge with VoiceAssistantCore for shared streaming logic. ✅ Done in commit `shared ws utils`. _Prio: Mittel_
- **gui/enhanced-voice-assistant.js**: consolidate with shared core modules to avoid duplication. _Prio: Mittel_
- **gui layout and design refresh**: reorganize GUI elements (status page, input placement, icon-only round buttons). _Prio: Niedrig_
- **gui animations**: implement matrix-rain response effect, avatar pulse, message flash. _Prio: Niedrig_

## WS-Server / Protokolle
- **ws_server/stt/in_memory.py**: implement streaming support without buffering entire audio. ✅ Done in commit `stt streaming`. _Prio: Hoch_
- **ws_server/compat/legacy_ws_server.py**: stream chunk-wise without buffering entire audio; log Kokoro voice detection errors instead of silent pass. ✅ Done in commit `legacy ws streaming`. _Prio: Mittel_
- **ws_server/routing/skills.py**: flesh out skill interface and routing logic. ✅ Done in commit `skill interface abc`. _Prio: Hoch_
- **ws_server/transport/fastapi_adapter.py**: implement FastAPI transport adapter. ✅ Done in commit `fastapi adapter`. _Prio: Niedrig_
- **ws_server/tts/text_sanitizer.py**: unify sanitizer, normalizer and chunking pipeline. ✅ Done in commit `unify text pipeline`. _Prio: Niedrig_
- **ws_server/tts/staged_tts/chunking.py**: review overlap with sanitizer/normalizer for unified pipeline. ✅ Done in commit `chunking pipeline unify`.
- **ws_server/tts/text_normalize.py**: clarify responsibilities with other sanitizer components. ✅ Done in commit `unify text pipeline`. _Prio: Niedrig_
- **ws_server/protocol/binary_v2.py**: verify PCM format and sample rate before processing. ✅ Done in commit `binary PCM validation`. _Prio: Hoch_
- **ws_server/metrics/collector.py**: track memory usage and network throughput metrics. ✅ Done in commit `metrics network throughput`. _Prio: Mittel_
- **ws_server/tts/staged_tts/staged_processor.py**: make crossfade duration configurable. ✅ Done in commit `staged tts crossfade env`. _Prio: Niedrig_
- **ws_server/compat/legacy_ws_server.py.backup.int_fix**: remove outdated backup file or merge changes into main compat module. ✅ Done in commit `remove legacy ws backup`. _Prio: Niedrig_
- **archive/legacy_ws_server/skills/__init__.py**: implement BaseSkill methods or remove legacy skill module. ✅ Done in commit `remove legacy skills module`. _Prio: Niedrig_

## Config
- **ws_server/tts/voice_aliases.py**: unify voice alias config with `config/tts.json` and environment. ✅ Done in commit `unify voice aliases`. _Prio: Niedrig_
- **config/tts.json**: align with `voice_aliases.py` to remove duplication. ✅ Done in commit `unify voice aliases`. _Prio: Niedrig_
- **env.example**: consolidate TTS defaults with `config/tts.json` to prevent drift. ✅ Done in commit `unify voice aliases`. _Prio: Niedrig_

## Dokumentation
- **docs/Refaktorierungsplan.md**: add TODO stubs for true streaming. ✅ Done in commit `docs true streaming stubs`. _Prio: Niedrig_
- **docs/GUI-TODO.md**: review and merge GUI tasks into central roadmap. ✅ Done in commit `gui todo merged`. _Prio: Niedrig_

## Tools & Scripts
- **start_voice_assistant.py**: replace silent `pass` blocks with explicit error handling. ✅ Done in commit `startup error handling`. _Prio: Niedrig_

## ❓ Offene Fragen
- ❓ Are VoiceAssistantCore and AudioStreamer both needed or can they be merged?
- ❓ Is the legacy WS server still required, or can the compat layer be dropped?
- ❓ Is `gui/enhanced-voice-assistant.js` still required or can its features be merged into the shared core modules?
