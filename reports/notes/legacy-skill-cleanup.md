# Legacy skill cleanup

## Design Notes
- Remove `archive/legacy_ws_server/skills/` since modern skills live in `ws_server/skills/`.
- No runtime references remain; deletion reduces confusion.
- Keep mapping in `DEPRECATIONS.md` for historical reference.
- Update `TODO-Index.md` to mark task complete.
