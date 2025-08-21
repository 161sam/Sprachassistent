# TTS Engines

This project can synthesize speech using different engines. Defaults are read from `.env` and can be overridden per request.

## `.env` settings

- `TTS_ENGINE` – default engine (`"piper"`, `"kokoro"` or `"zonos"`)
- `TTS_VOICE` – default voice identifier
- `TTS_SPEED` – playback speed (1.0 = normal)
- `TTS_VOLUME` – output volume factor (1.0 = normal)

## WebSocket overrides

Clients may override any of the settings by including them in the request:

```json
{
  "type": "speak",
  "text": "Wie spät ist es?",
  "tts_engine": "piper",
  "tts_voice": "de-eva_k-low",
  "tts_speed": 1.2,
  "tts_volume": 0.8
}
```

## Available voices

### Piper
- `de-thorsten-low` (German)
- `en-amy-low` (English)

### Kokoro
- `af_sarah` (English)
- `de_female` (German)
