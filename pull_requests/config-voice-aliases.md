# Summary
- load TTS voice aliases from `config/tts.json` to remove duplicated mappings
- drop obsolete env vars and document config source of truth

# Risk
- minimal: loader only reads JSON and defaults remain unchanged

# Rollback
- revert commit `refactor(config): unify voice alias configuration`
