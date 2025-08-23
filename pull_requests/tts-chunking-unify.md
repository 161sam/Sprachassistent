# Summary
- expose `limit_and_chunk` for staged TTS and centralize sanitization
- update imports, tests and docs to new chunking API

# Risk
- minimal: function rename and sanitization path

# Rollback
- revert commit `chunking pipeline unify`
