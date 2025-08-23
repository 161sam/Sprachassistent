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

## Piper+Zonos (Staged)

With *staged* playback the assistant streams a short **Piper** intro while the
main answer is generated with **Zonos** in the background.  Set
`STAGED_TTS_INTRO_ENGINE=piper` and `STAGED_TTS_MAIN_ENGINE=zonos` in your
environment to force this combination.  The processor checks that each engine
is loaded for the requested voice; if Piper is unavailable the intro is
skipped and Zonos handles the whole response.
