# Decision Index

- Last verified: 2026-07-27
- Authority: explicit decisions in `93_运行记录/决策日志.md` and current user confirmation

| Decision | Status | Consequence | Source | Reconsider when |
| --- | --- | --- | --- | --- |
| DEC-001 | Accepted | Use `91_知识库/` as hard generation constraints instead of optional reading. | `93_运行记录/决策日志.md` | A replacement validation system is implemented. |
| DEC-002 | Accepted | Use six repository-local Claude skills to encode the production workflows. | `93_运行记录/决策日志.md` | The agent runtime or workflow model changes materially. |
| DEC-003 | Accepted | Use reference art plus identity/style/clue locks to control character consistency. | `93_运行记录/决策日志.md` | A tested generation model makes the locks unnecessary. |
| DEC-004 | Accepted | Use ffmpeg for batch video production; reserve Jianying drafts for higher-value manual refinement. | `93_运行记录/决策日志.md` | Export automation or production volume changes. |
| DEC-005 | Accepted | Use edge-tts because word timing supports the subtitle pipeline. | `93_运行记录/决策日志.md` | Quality, availability, licensing, or timing support becomes unsuitable. |
| DEC-006 | Accepted | Render knowledge-line text as HTML/cards rather than asking diffusion models to draw Chinese text. | `93_运行记录/决策日志.md` | Image models demonstrate reliable, editable Chinese typography. |
| DEC-007 | Accepted | Keep authenticated publishing and private data collection on local Windows; do not share platform cookies with cloud sessions. | `93_运行记录/决策日志.md` | An approved secure publishing service replaces local authentication. |
| DEC-008 | Accepted | Do not add n8n, Dify, or Coze as another orchestration layer for the initial workflow. | `93_运行记录/决策日志.md` | A concrete integration need outweighs the maintenance cost. |
| DEC-009 | Accepted | Create a new GitHub repository for this recovered project and use `main` as the integration branch. | User confirmation, 2026-07-27 | Repository ownership or collaboration needs change. |
