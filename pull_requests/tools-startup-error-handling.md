# Summary
- log failures during process cleanup and stdout monitoring in `start_voice_assistant.py`
- document design decision for explicit error handling

# Risk
- Minimal: only affects developer startup script.

# Rollback
- Revert commit `fix(tools): log subprocess errors during startup`.
