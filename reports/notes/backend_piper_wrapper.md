## Design Note: Remove deprecated Piper wrapper

- The wrapper `backend/tts/piper_tts_engine.py` merely re-exported the new engine.
- All consumers should import `PiperTTSEngine` from `ws_server.tts.engines.piper`.
- Delete the wrapper and update references.
- No API changes: class name and behavior remain identical.
- Tests updated to import from the new module.
