# Legacy WS Compat Layer

## Context
`ws_server/transport/server.py` imports `ws_server.compat.legacy_ws_server` as the runtime server. This indicates that the compat layer is still the active implementation.

## Decision
Keep `legacy_ws_server` in place for now. Removing it would require a new server module exposing the same API. The TODO is marked as fixed with a note that the compat layer remains required until a replacement exists.

## Follow-up
- Introduce a modern server module and update transport to use it.
- Once migrated, deprecate `ws_server/compat/legacy_ws_server.py`.
