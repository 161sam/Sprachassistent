## Design Note: Explicit sample-rate error handling

- `_read_sample_rate` silently ignored JSON read errors.
- Add logging and raise `TTSInitializationError` when the rate cannot be read.
- Preserve special-case fallback for legacy `de_DE-thorsten-low` model.
- Removal of backend wrapper makes "keep in sync" comment obsolete.
