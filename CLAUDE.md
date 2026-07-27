@AGENTS.md

# Claude Code adapter

- Use the project Skills in `.claude/skills/`; they delegate to `.agents/skills/`.
- Treat `.context/` as canonical project context.
- Stop and report any missing canonical Skill path before modifying project files.
