# Context schema

Use the repository's established context location when it is coherent. Otherwise create `.context/` with the four files below.

## Evidence labels

- `[VERIFIED]`: confirmed by code, tests, configuration, Git, or observed behavior
- `[DOCUMENTED]`: explicitly documented but not reverified
- `[INFERRED]`: supported by evidence but not directly proven
- `[CONFLICT]`: credible sources disagree
- `[STALE]`: a source clearly describes an older state
- `[UNKNOWN]`: repository evidence is insufficient

Attach a path, command, test, commit, decision, or user confirmation to consequential claims.

## PROJECT.md

Store durable information: product purpose, users, scope, non-goals, core capabilities, technology, architecture, primary flows, invariants, trust boundaries, and stable development entry points. Do not copy a directory listing or temporary task status.

## CURRENT.md

Keep the one-minute resume point: verification date, branch, commit, worktree state, current phase, working capabilities, recent changes, broken or uncertain areas, checks run and not run, next three actions, and the exact resume file or command.

## REQUIREMENTS.md

Track each meaningful requirement with an ID, lifecycle status, evidence label, concise statement, and source. Use only `Implemented`, `Accepted`, `Candidate`, `Deferred`, `Rejected`, or `Unknown`. Qualify partial or unverified implementation in the evidence column.

## DECISIONS.md

Use this as an index of durable decisions and ADRs. Record the decision ID, status, consequence, authoritative source, and reconsideration trigger. Do not manufacture historical decisions or treat draft architecture documents as accepted.

## Conversation history

Use `history/` only when prior conversation is required to preserve intent or continuity. Export user and assistant messages, record source session IDs and dates, and omit system/developer instructions, hidden reasoning, tool calls, tool outputs, secrets, and unrelated sessions. Keep `history/INDEX.md` concise.

## Update policy

- Update `CURRENT.md` after material development-state changes.
- Update `REQUIREMENTS.md` when intent or lifecycle state changes.
- Update `PROJECT.md` only for durable product or architecture changes.
- Add an ADR for persistent cross-module decisions, then update `DECISIONS.md`.
- Avoid logs or timestamps that create churn without improving recovery.
