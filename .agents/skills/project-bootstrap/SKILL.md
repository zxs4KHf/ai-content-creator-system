---
name: project-bootstrap
description: Reconstruct and materialize verified context for an existing repository from code, tests, configuration, documentation, Git history, and prior plans. Use when entering an unfamiliar or long-paused project, when documentation may be stale or contradictory, when `.context/` is missing or unreliable, or before handing a repository to a new coding agent. Do not use for routine small changes when current context is already trustworthy.
---

# Project Bootstrap

Establish reusable, evidence-backed project context before implementation. Begin with reconnaissance and preserve the existing working state.

Read [references/context-schema.md](references/context-schema.md) before creating or materially restructuring context files. Use the files under `assets/` only when the repository has no coherent equivalent; never overwrite an existing context system blindly.

## 1. Protect the workspace

- Locate the repository root, branch, HEAD, worktree changes, and applicable Agent instructions.
- Discover existing context, memory, ADR, planning, and handoff systems before proposing new files.
- Exclude dependencies, generated files, binaries, secrets, databases, logs, and scratch content from broad scans.
- Start read-only. Do not clean, reset, install dependencies, start services, or expose secrets.
- State a short checkpoint with the repository state and highest-signal sources.

## 2. Build a surface map

Inspect the root and one or two directory levels first:

- manifests and workspace configuration
- README and documentation indexes
- build, test, lint, CI, deployment, and environment templates
- application entry points, migrations, API definitions, and tests
- recent commits, tags, and branches

Identify the runtime, core modules, validation commands, and next files worth reading. Do not recursively summarize every file.

## 3. Recover runtime and architecture

Read targeted entry points, core modules, state stores, APIs, integrations, and tests. Establish:

- the problem, user, and product boundary
- core user and system flows
- module responsibilities and data flow
- invariants, trust boundaries, and regression hotspots
- safe install, start, test, and verification paths

Prefer observed behavior and executable evidence over prose descriptions.

## 4. Recover intent and current state

Compare current evidence with docs, accepted ADRs, Git history, TODOs, old plans, and conversation records. For large transcripts, extract historical user requests before reading Agent responses.

Classify requirements as `Implemented`, `Accepted`, `Candidate`, `Deferred`, `Rejected`, or `Unknown`. Mark contradictions rather than silently choosing a side. Never convert an old idea into an accepted requirement without supporting evidence or user confirmation.

Use `[VERIFIED]`, `[DOCUMENTED]`, `[INFERRED]`, `[CONFLICT]`, `[STALE]`, and `[UNKNOWN]` for consequential claims.

## 5. Materialize context

Prefer the repository's established coherent context system. Otherwise create or update:

- `.context/PROJECT.md`
- `.context/CURRENT.md`
- `.context/REQUIREMENTS.md`
- `.context/DECISIONS.md`

Keep `CURRENT.md` short enough for a one-minute recovery. Preserve detailed source material instead of duplicating it. If prior Codex rollout files are necessary for continuity, export only user and assistant messages into `history/` and create a concise index.

Add thin Agent adapters only when useful and compatible with existing instructions. Do not replace a substantial `AGENTS.md`, `CLAUDE.md`, or another tool's rules without integrating its current content.

## 6. Verify and report

- Run only safe, relevant, proportionate checks.
- Confirm the worktree was not unexpectedly changed.
- Distinguish checks run from checks not run.
- Report a 60-second recovery brief, repository map, current state, conflicts, unknowns, three next actions, and the smallest recommended next action.
- Ask no more than three focused questions, only after repository evidence is exhausted.

## Completion criteria

Finish only when another Agent can read the repository entry instructions and `CURRENT.md`, understand what the project is, identify verified facts and uncertainty, and begin the exact next action without another full scan.
