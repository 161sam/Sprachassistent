# Summary
- enforce explicit skill plugin interface via abstract base class
- add async intent router test covering skill dispatch
- assert Flowise URL presence for type safety

# Risk
- Minimal: existing skill plugins must implement required methods, which they already do.

# Rollback
- Revert commit `skill interface abc` to restore previous dynamic skill handling.
