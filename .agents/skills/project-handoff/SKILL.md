---
name: project-handoff
description: Capture a verified, repository-local handoff for the next coding agent or future session. Use when pausing material work, switching agents or devices, ending a development session, reaching a blocker, or when the user asks to save progress so work can continue later. Update the canonical current-state file and report exact outcomes, checks, risks, and next action without dumping a raw transcript.
---

# Project Handoff

Leave the repository in a state another Agent can resume without reconstructing the entire session.

## 1. Reconcile the workspace

- Inspect branch, HEAD, and worktree changes.
- Identify files changed during the task and preserve unrelated user changes.
- Recheck the task outcome against current files and behavior.
- Run the narrowest relevant verification still needed and safe to execute.
- Record checks not run and why.

## 2. Update canonical context

Update `.context/CURRENT.md` or the repository's established equivalent with:

- verification date, branch, commit, and worktree state
- current phase and last completed outcome
- what works now
- blockers, risks, contradictions, and unknowns
- checks run and checks not run
- next three actions
- one exact next action with starting files or command

When the repository uses an ignored `.context/LOCAL.md`, put machine usernames, absolute local paths, private project names, and local registrations there instead of public context files.

Update `REQUIREMENTS.md` only when requirement status or user intent changed. Update `PROJECT.md` only for durable scope or architecture changes. Update `DECISIONS.md` only when a durable decision was accepted or superseded.

Do not paste the entire chat, tool log, diff, or test output into canonical context. Put necessary historical conversation in a sanitized `history/` transcript and link it from an index.

## 3. Check resume quality

Confirm that a fresh Agent can answer from repository files:

- What is this project?
- What just changed?
- What is verified?
- What is uncertain or blocked?
- What should happen next, exactly?

If any answer depends only on the current chat, improve the repository handoff before finishing.

## 4. Report to the user

Lead with the outcome. Include:

- changed files and behavior
- checks passed and not run
- remaining risks or blockers
- exact next action
- whether changes are committed or still local

Avoid claiming completion when required work remains. A blocker is not a completion state.
