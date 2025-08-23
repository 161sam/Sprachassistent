# ws_server/tts/text_sanitizer.py

## Context
`pre_sanitize_text` chained basic and strict sanitizers but duplicated the normalizer logic.

## Decision
Import `basic_sanitize` from `text_normalize` and allow `pre_sanitize_text` to accept a `mode` argument. The function remains the strict stage while `text_normalize.sanitize_for_tts` wraps it for callers.

## Consequences
- Eliminates overlap between normalizer and sanitizer.
- Simplifies future chunking pipeline integration.
