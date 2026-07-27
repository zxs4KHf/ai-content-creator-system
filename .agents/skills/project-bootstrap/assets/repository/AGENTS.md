# Repository Agent Guide

Keep this file short. Project facts belong in `.context/`; repeatable procedures belong in Skills.

## Start here

Before material work:

1. Read `.context/CURRENT.md` for the current state and next action.
2. Read `.context/PROJECT.md` for durable scope and architecture.
3. Read `.context/REQUIREMENTS.md` or `.context/DECISIONS.md` only when relevant.
4. Compare written context with the current branch, HEAD, worktree, code, and tests.
5. Use `project-bootstrap` when context is missing, stale, or contradictory.
6. Use `project-resume` after interruption and `project-handoff` before pausing material work.

## Evidence and safety

- Prefer current code and observed behavior, then tests/configuration, accepted decisions, current context, Git history, old plans, and inference.
- Label consequential uncertainty as `[VERIFIED]`, `[DOCUMENTED]`, `[INFERRED]`, `[CONFLICT]`, `[STALE]`, or `[UNKNOWN]`.
- Preserve uncommitted changes and begin reconnaissance read-only.
- Do not expose secrets or start live services merely to understand the repository.
- Run the narrowest relevant checks and state what was not checked.

## Context maintenance

- Keep `.context/CURRENT.md` as the one-minute resume point.
- Update requirements and decisions only when their durable status changes.
- Store sanitized conversation history under `history/` only when needed for intent or continuity.
