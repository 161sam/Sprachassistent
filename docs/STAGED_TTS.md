# Staged TTS – Intro/Main Pipeline

- Intro: Piper (CPU) für sofortiges Feedback, Länge via `STAGED_TTS_MAX_INTRO_LENGTH`.
- Main: Zonos (GPU) für hochwertigen Hauptinhalt; Fallback auf Piper bei Fehlern/Timeouts.
- Crossfade: Equal-Power, Standard `STAGED_TTS_CROSSFADE_MS=100` (80–120 ms empfohlen).
- Chunking: Ziel 80–180 Zeichen/Chunk, Gesamt ≤500 Zeichen. Prosodie-Optimierung vor dem Chunking.

## Qualität
- Kein per‑Chunk Peak‑Normalize im Adapter; eine zentrale Loudness‑Normalisierung im Manager (`TTS_LOUDNESS_NORMALIZE=1`).
- Ziel‑Samplerate per `TTS_TARGET_SR` (Standard 24000). Intro/Main werden darauf resampled.
- Soft‑Limiter mit `TTS_LIMITER_CEILING_DBFS` (Standard −1.0 dBFS).

## Steuerung
- Laufzeitsteuerung via GUI oder ENV:
  - `STAGED_TTS_INTRO_ENGINE`, `STAGED_TTS_MAIN_ENGINE`
  - `STAGED_TTS_CROSSFADE_MS`, `STAGED_TTS_CHUNK_SIZE_MIN/MAX`, `STAGED_TTS_MAIN_MAX_CHUNKS`

## Hinweise
- Frontend verändert keine Abspielgeschwindigkeit; Pitch wird beibehalten.
- Optionaler Binär‑Pfad bleibt hinter `WS_BINARY_AUDIO` abgeschaltet; Default sind JSON‑WAV‑Chunks.
