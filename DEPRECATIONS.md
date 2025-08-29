# Deprecations

| Old path | Replacement |
| --- | --- |
| `ws_server/transport/enhanced_ws_server.py` | `ws_server/transport/server.py` |
| `ws_server/transport/server_enhanced_entry.py` | `ws_server/cli.py` |
| `backend/ws-server/enhanced_websocket_server.py` | `ws_server/transport/server.py` |
| `backend/ws-server/ws-server-enhanced.py` | `ws_server/cli.py` |
| `backend/ws-server/integration/migrate_to_binary.py` | _archived (obsolete)_ |
| `backend/ws-server/migration_complete.py` | _archived (obsolete)_ |
| `backend/ws-server/ws-server.py` | `ws_server/cli.py` |
| `backend/ws-server/ws-server-minimal.py` | `ws_server/compat/legacy_ws_server.py` |
| `backend/ws-server/staged_tts/` | `ws_server/tts/staged_tts/` |
| `backend/ws-server/` | `archive/legacy_ws_server/` |
| `backend/ws-server/README.md` | `archive/legacy_ws_server/README.md` |
| `archive/legacy_ws_server/skills/` | `ws_server/skills/` |
| `voice-assistant-apps/shared/core/AudioStreamer.js` (manual queue) | sequence-based playback with prebuffered crossfade in same file |
| `docs/GUI-TODO.md` | entries moved to `TODO-Index.md` |

| File | New Location | Reason | Replacement |
| --- | --- | --- | --- |
| `uvicorn` | `archive_legacy/uvicorn` | Stray PostScript artifact | None |
| `ws_server/tts/staged_tts/staged_processor.py` | (kept, deprecated) | Duplicated staged TTS implementation | Use `ws_server.tts.staged_tts.adapter` |


## Repo hygiene run at 2025-08-29 08:12:06
