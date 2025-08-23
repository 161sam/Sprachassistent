# Design Notes: Unify Voice Alias Configuration

- Load voice alias mapping from `config/tts.json` at import time.
- Use `EngineVoice` dataclass to parse per-engine settings from JSON.
- Replace hard-coded `VOICE_ALIASES` dictionary.
- Keep JSON as the single source of truth for voice/engine mapping.
- Remove TTS voice settings from `.env` to prevent drift.
- Update tests to rely on JSON-derived mapping.
