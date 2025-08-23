# ws_server/tts/text_normalize.py

## Context
`sanitize_for_tts` duplicated basic normalization and served as a public API separate from the strict sanitizer.

## Decision
Extracted `basic_sanitize` for lightweight cleanup and delegated `sanitize_for_tts` to `text_sanitizer.pre_sanitize_text`.
This forms a single entry point for TTS text preprocessing and avoids circular imports by lazy importing in the wrapper.

## Consequences
- `text_sanitizer` now imports `basic_sanitize` and accepts an optional `mode`.
- Callers importing `sanitize_for_tts` receive the full pipeline.
