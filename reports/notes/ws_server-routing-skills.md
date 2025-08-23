# ws_server/routing/skills.py

## Context
Existing `BaseSkill` class only documented TODOs and allowed implementations to omit core methods, leading to weak contracts. Routing logic lacked tests.

## Decision
Introduce `BaseSkill` as an abstract base class with explicit `can_handle` and `handle` methods. This enforces implementation in concrete skills and clarifies the contract. Add unit test for `IntentRouter.route` to ensure skills are used.

## Consequences
- Skill plugins must implement both methods.
- Loading logic unchanged; test coverage increased for routing behaviour.
