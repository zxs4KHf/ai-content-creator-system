---
name: project-resume
description: Restore a repository's verified working context and continue an interrupted task with minimal re-reading. Use when returning after a pause, opening the project in another terminal or agent, continuing from a handoff, or when the user asks what was happening and what to do next. Escalate to project-bootstrap when canonical context is missing, materially stale, or contradicted by current repository evidence.
---

# Project Resume

Restore the shortest trustworthy path from repository state to useful work.

## 1. Load the resume point

- Read applicable Agent instructions.
- Read `.context/CURRENT.md` first.
- Read `.context/PROJECT.md` for durable boundaries.
- Load `REQUIREMENTS.md`, `DECISIONS.md`, ADRs, history, and module docs only when the current task needs them.
- If the repository uses another coherent context location, follow its navigation instead of creating duplicates.

## 2. Verify drift

Compare the written resume point with:

- branch, HEAD, and worktree changes
- relevant source files and tests
- recent commits since the recorded checkpoint
- active plans or handoffs referenced by `CURRENT.md`

Classify differences as expected work, stale context, contradiction, or unknown. Preserve work from other terminals. Do not reset or clean.

Use `project-bootstrap` before implementation when the resume point is missing, cannot explain the repository, or is materially contradicted by evidence.

## 3. Reconstruct the active task

State a concise brief containing:

- project purpose and current phase
- last verified outcome
- current worktree state
- unresolved risks or decisions
- exact next action and the files or command needed to start it

If material intent remains ambiguous after reading repository evidence and history, ask one focused question with the evidence and the choice that changes the work.

## 4. Continue safely

When the user's request includes implementation, proceed from the verified next action. Use narrow checks first and keep commentary concise. Do not spend the turn only summarizing if safe authorized work remains.

Update `.context/CURRENT.md` when the working state, risks, checks, or next action materially changes. Update other context files only when their durable content changes.

## Completion criteria

Finish the resume phase when the active task, repository state, risks, and next action are verified enough to continue without a full rescan. Use `project-handoff` at the end of material work.
