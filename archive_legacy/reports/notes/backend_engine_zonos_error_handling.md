# Zonos Engine Error Handling

## Context
`backend/tts/engines.zonos.py` silently ignores failures when importing the text sanitizer and when applying speed conditioning. This hides configuration errors and hampers debugging.

## Proposal
- Wrap the sanitizer import in `try/except` and log a warning if it fails.
- Validate the `speed` parameter; on failure, log a warning including the invalid value.
- Preserve synthesis flow by continuing with defaults after logging.
