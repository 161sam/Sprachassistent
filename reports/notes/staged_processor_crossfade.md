**Goal:** Make crossfade duration configurable via environment variable for staged TTS.

**Design:**
- Extend `StagedTTSConfig` with `from_env` classmethod.
- Allow overriding `crossfade_duration_ms` using `STAGED_TTS_CROSSFADE_MS`.
- `StagedTTSProcessor` uses `StagedTTSConfig.from_env()` when no config supplied.
- Ensure chunk messages include the configured crossfade value.
