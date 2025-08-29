# Upgrade Notes

## TTS quality (German defaults)
- Default TTS language: `de-DE` (config + GUI control).
- Staged‑TTS tuned: intro_max_chunks=1, max_intro_length=80, crossfade=60ms, chunk sizes 100–220.
- Sanitizer removes combining marks (fixes Piper "Missing phoneme from id map").
- Default speaking speed reduced to 0.92x for calmer delivery.
- Optional post‑FX: loudness normalize and soft limiter (enable with `TTS_LOUDNESS_NORMALIZE=1`).

## Unified server entrypoint
- Start the backend via `python -m ws_server.cli`.
- Legacy scripts under `backend/ws-server/` have been removed; update any
  custom wrappers to point to the new entrypoint.
- The desktop app expects the server at this entrypoint; start it before
  running `npm start` in `voice-assistant-apps/desktop`.

## LLM Model Listings
- WebSocket messages `get_llm_models` and `switch_llm_model` now expose
  separate lists for available and loaded models.
- Backend tracks the chosen LLM model and clears chat history when switching.

## Migration
- Clients should expect `llm_models` responses in the form:
  ```json
  {
    "type": "llm_models",
    "available": ["model-a", "model-b"],
    "loaded": ["model-a"],
    "current": "model-a"
  }
  ```
- When selecting a new model send:
  ```json
  {
    "type": "switch_llm_model",
    "model": "model-b"
  }
  ```

## Piper TTS sanitization
- Text for Piper is sanitized with a final guard.
- All combining marks (U+0300–U+036F) are removed before synthesis to prevent "Missing phoneme from id map" warnings.
- Optional debug logging via `PIPELINE_DEBUG_SANITIZE=1` shows how many Zeichen entfernt wurden.

## Voice list rollback (cleanup)

- Removed: dynamic scan of `spk_cache/` and training/sample files as selectable voices.
- Kept: small, static base voices (e.g. `de-thorsten-low`, `de-karlsson-low`, previous defaults).
- Rationale: large voice lists (training data) caused oversized WS payloads and performance issues.
- Effect: the GUI shows a compact static selection again. Custom Zonos samples can still improve quality but are not auto-listed as voices.
- Repo hygiene: `spk_cache/` and `data/` are now ignored via `.gitignore`. See `scripts/cleanup_spk_cache.sh` and `scripts/git_remove_large_files.sh` for cleanup options.
- CLI consolidation
- `va` ist die einzige CLI. `python -m ws_server.cli` ist veraltet und ruft intern `va` auf. Siehe `docs/cli.md`.

- Zonos voice mapping (thorsten)
- Zonos bevorzugt lokale Modelle (`models/zonos/**` oder `ZONOS_LOCAL_DIR`). Sprecher‑Samples werden aus `spk_cache/thorsten.*` geladen; fehlt das Sample, wird eine Default‑Stimme verwendet (Warnung, kein Fehler).
