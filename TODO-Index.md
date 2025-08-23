# 📌 Zentrale TODO-Übersicht

## Backend
- **backend/tts/piper_tts_engine.py**: remove deprecated wrapper for Piper engine. _Prio: Niedrig_
- **ws_server/tts/engines/piper.py**: keep implementation in sync with backend wrapper; handle sample rate read errors explicitly. _Prio: Niedrig_
- **torch.py / torchaudio.py / soundfile.py**: replace stub modules with real dependencies or dedicated mocks. _Prio: Niedrig_
- **piper/__init__.py**: replace stub with real piper dependency. _Prio: Niedrig_
- **backend/tts/engine_zonos.py**: replace silent exception passes with explicit error handling for sanitizer import and speed conditioning. _Prio: Niedrig_

## Frontend
- **voice-assistant-apps/shared/core/VoiceAssistantCore.js**: consolidate with AudioStreamer to avoid duplicate streaming logic. _Prio: Mittel_
- **voice-assistant-apps/shared/core/AudioStreamer.js**: merge with VoiceAssistantCore for shared streaming logic. _Prio: Mittel_
- **gui/enhanced-voice-assistant.js**: consolidate with shared core modules to avoid duplication. _Prio: Mittel_

## WS-Server / Protokolle
- **ws_server/stt/in_memory.py**: implement streaming support without buffering entire audio. ✅ Done in commit `stt streaming`. _Prio: Hoch_
- **ws_server/compat/legacy_ws_server.py**: stream chunk-wise without buffering entire audio; log Kokoro voice detection errors instead of silent pass. _Prio: Mittel_
- **ws_server/routing/skills.py**: flesh out skill interface and routing logic. ✅ Done in commit `skill interface abc`. _Prio: Hoch_
- **ws_server/transport/fastapi_adapter.py**: implement FastAPI transport adapter. _Prio: Niedrig_
- **ws_server/tts/text_sanitizer.py**: unify sanitizer, normalizer and chunking pipeline. _Prio: Niedrig_
- **ws_server/tts/staged_tts/chunking.py**: review overlap with sanitizer/normalizer for unified pipeline. _Prio: Mittel_
- **ws_server/tts/text_normalize.py**: clarify responsibilities with other sanitizer components. _Prio: Niedrig_
- **ws_server/protocol/binary_v2.py**: verify PCM format and sample rate before processing. ✅ Done in commit `binary PCM validation`. _Prio: Hoch_
- **ws_server/metrics/collector.py**: track memory usage and network throughput metrics. ✅ Done in commit `metrics network throughput`. _Prio: Mittel_
- **ws_server/tts/staged_tts/staged_processor.py**: make crossfade duration configurable. _Prio: Niedrig_
- **ws_server/compat/legacy_ws_server.py.backup.int_fix**: remove outdated backup file or merge changes into main compat module. _Prio: Niedrig_
- **archive/legacy_ws_server/skills/__init__.py**: implement BaseSkill methods or remove legacy skill module. _Prio: Niedrig_

## Config
- **ws_server/tts/voice_aliases.py**: unify voice alias config with `config/tts.json` and environment. _Prio: Niedrig_
- **config/tts.json**: align with `voice_aliases.py` to remove duplication. _Prio: Niedrig_
- **env.example**: consolidate TTS defaults with `config/tts.json` to prevent drift. _Prio: Niedrig_

## Dokumentation
- **docs/Refaktorierungsplan.md**: add TODO stubs for true streaming. _Prio: Niedrig_
- **docs/GUI-TODO.md**: review and merge GUI tasks into central roadmap. _Prio: Niedrig_

## Tools & Scripts
- **start_voice_assistant.py**: replace silent `pass` blocks with explicit error handling. _Prio: Niedrig_

## ❓ Offene Fragen
- ❓ Are VoiceAssistantCore and AudioStreamer both needed or can they be merged?
- ❓ Is the legacy WS server still required, or can the compat layer be dropped?
- ❓ Are the torch/torchaudio/soundfile stubs still necessary once real libraries are installed?
- ❓ Is `gui/enhanced-voice-assistant.js` still required or can its features be merged into the shared core modules?
- ❓ Can `ws_server/compat/legacy_ws_server.py.backup.int_fix` be removed after verifying no changes are needed?
- ❓ Is the archived legacy skill system (`archive/legacy_ws_server`) still required or can it be removed entirely?
