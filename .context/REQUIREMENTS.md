# Requirements

- Last verified: 2026-07-28
- Sources: user confirmation, `README.md`, `00_账号定位/账号定位.md`, `93_运行记录/决策日志.md`, Python tools, templates, and the current story review form

| ID | Status | Evidence | Requirement | Primary source |
| --- | --- | --- | --- | --- |
| REQ-001 | Implemented | [DOCUMENTED] | Organize production into research, generation, assets/video, publishing, and review stages with G1/G2/G3 human gates. | `README.md` |
| REQ-002 | Implemented | [VERIFIED] | Represent content state by moving one complete content folder through production directories. | `README.md`, repository structure |
| REQ-003 | Implemented | [VERIFIED] | Store reusable process templates separately from hard generation constraints. | `90_模板库/`, `91_知识库/` |
| REQ-004 | Implemented | [VERIFIED] | Provide local tools for image generation, TTS, subtitle alignment, video assembly, and Jianying drafts; the TTS/subtitle/video path has been exercised on Windows. | `92_工具箱/*.py`, first story artifacts |
| REQ-005 | Implemented | [VERIFIED] | Require stable character reference art and identity/style locks before batch story illustration. | `91_知识库/K5_生图一致性手册.md`, C001/C002 assets |
| REQ-006 | Accepted | [DOCUMENTED] | Keep authenticated publishing and private platform-data operations on local Windows only. | `README.md`, `93_运行记录/决策日志.md` |
| REQ-007 | Accepted | [VERIFIED] | Require explicit confirmation immediately before publishing, a platform declaration, and a persistent visible AI label in video candidates. | `README.md`, `91_知识库/K6_AI合规红线.md`, `align_subtitles.py` |
| REQ-008 | Accepted | [DOCUMENTED] | Do not invent facts; verify or remove uncertain claims before publication. | `README.md`, `91_知识库/K6_AI合规红线.md` |
| REQ-009 | Candidate | [DOCUMENTED] | Deploy Xiaohongshu MCP for semi-automated local publishing after the first content loop is validated. | `README.md` roadmap |
| REQ-010 | Deferred | [DOCUMENTED] | Add a weekly inbox-processing and review reminder after the repository and first production loop are stable. | `README.md` roadmap |
| REQ-011 | Unknown | [UNKNOWN] | Validate the platform limits currently marked unverified against the live platform backends. | `91_知识库/K2_平台规格手册.md` |
| REQ-012 | Accepted | [VERIFIED] | Maintain the project in GitHub and integrate reviewed work into `main`. | User confirmation, 2026-07-27 |

Allowed statuses: `Implemented`, `Accepted`, `Candidate`, `Deferred`, `Rejected`, `Unknown`.
