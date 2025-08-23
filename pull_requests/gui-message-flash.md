# Summary
- add flash animation to live text overlay when new assistant text appears

# Testing
- `pytest -q`

# Risk
- Low: only touches GUI overlay styling and event handler

# Rollback
- Revert commit `feat(gui): flash overlay on new text`
