# start_voice_assistant.py – explicit error handling

## Context
`start_voice_assistant.py` used `pass` in exception handlers when killing processes or reading subprocess output. This hid failures and made debugging difficult.

## Design
- Replace `pass` with `print` logging that includes PID or operation context.
- Keep process cleanup flow intact; do not re-raise to avoid stopping cleanup.
- Annotate fixes with `# TODO-FIXED(2025-08-23)` for traceability.
