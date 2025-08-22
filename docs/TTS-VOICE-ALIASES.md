# Canonical TTS Voices

The backend uses **canonical voice names** (e.g. `de-thorsten-low`) that map to engine-specific assets.
Mappings live in `ws_server/tts/voice_aliases.py`.

## Available Voices

- `de-thorsten-low` – German male voice (Piper: `models/piper/de-thorsten-low.onnx`, Zonos: `thorsten`)
- `de_DE-thorsten-low` – locale-style alias for `de-thorsten-low`

## Adding a Voice
1. Choose a new canonical name.
2. Add per-engine `EngineVoice` entries in `voice_aliases.py`.
3. Point Piper to the `.onnx` model and set `voice_id` for Zonos/Kokoro.

## Validation
`validate_voice_assets()` checks that the assets exist and logs a summary at startup.
Missing Piper models or voice IDs produce warnings.

## Configuration
Set the canonical name via `TTS_VOICE` in `.env` (defaults to `de-thorsten-low`).
Optional post-processing:
- `TTS_TARGET_SR` – resample to target sample rate (Hz).
- `TTS_LOUDNESS_NORMALIZE` – set to `1` to normalize output gain.

## Troubleshooting
- "Piper model missing": ensure the `.onnx` file path is correct.
- "Zonos/Kokoro disabled": add a mapping or adjust `TTS_VOICE`.
