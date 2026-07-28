# Decision Index

- Last verified: 2026-07-28
- Authority: explicit decisions in `93_运行记录/决策日志.md` and current user confirmation

| Decision | Status | Consequence | Source | Reconsider when |
| --- | --- | --- | --- | --- |
| DEC-001 | Accepted | Use `91_知识库/` as hard generation constraints instead of optional reading. | `93_运行记录/决策日志.md` | A replacement validation system is implemented. |
| DEC-002 | Accepted | Use six repository-local Claude skills to encode the production workflows. | `93_运行记录/决策日志.md` | The agent runtime or workflow model changes materially. |
| DEC-003 | Accepted | Use reference art plus identity/style/clue locks to control character consistency. | `93_运行记录/决策日志.md` | A tested generation model makes the locks unnecessary. |
| DEC-004 | Accepted | Use ffmpeg for batch video production; reserve Jianying drafts for higher-value manual refinement. | `93_运行记录/决策日志.md` | Export automation or production volume changes. |
| DEC-005 | Superseded | Keep edge-tts only as the verified internal baseline/fallback; naturalness, English quality, third-party commercial authorization, and SLA are insufficiently proven for the long-term default. | User voice feedback, K10, 2026-07-28 voice research | An official commercial path and blind/stability results justify production use. |
| DEC-006 | Accepted | Render knowledge-line text as HTML/cards rather than asking diffusion models to draw Chinese text. | `93_运行记录/决策日志.md` | Image models demonstrate reliable, editable Chinese typography. |
| DEC-007 | Accepted | Keep authenticated publishing and private data collection on local Windows; do not share platform cookies with cloud sessions. | `93_运行记录/决策日志.md` | An approved secure publishing service replaces local authentication. |
| DEC-008 | Accepted | Do not add n8n, Dify, or Coze as another orchestration layer for the initial workflow. | `93_运行记录/决策日志.md` | A concrete integration need outweighs the maintenance cost. |
| DEC-009 | Accepted | Create a new GitHub repository for this recovered project and use `main` as the integration branch. | User confirmation, 2026-07-27 | Repository ownership or collaboration needs change. |
| DEC-010 | Accepted | Use the TTS manifest for one-image-per-segment timing; use an explicit validated image timeline when one narration segment splits into multiple shots. | `build_video.py`, first story 3A/3B split | A richer editor timeline replaces the current JSON contract. |
| DEC-011 | Accepted | Keep the first B 站 workflow pilot free of BGM/SFX unless source and license are verified; narration quality and workflow validation take priority. | First story G3 self-check | A licensed music/SFX library is added. |
| DEC-012 | Accepted | Generate a persistent visible `AI生成内容` label in publish-candidate ASS subtitles in addition to platform declarations. | `align_subtitles.py --ai-label`, compliance self-review | Applicable law or platform labeling mechanics change materially. |
| DEC-013 | Accepted | Split shots by information-state change; use `F0 → optional K → F1`, separate subject/environment/camera channels, and keep a deterministic full-film baseline before upgrading at most 2–3 hero shots. | K8, motion research, user motion feedback | Published retention and controlled motion experiments support a better rule. |
| DEC-014 | Accepted | Incubate four column promises inside one account before creating multiple same-platform accounts; require at least three samples per unit, compare within platform/window, and use 70/20/10 only after a stable core promise exists. | K9, matrix research, user matrix direction | Repeated account data and current platform rules support splitting. |
| DEC-015 | Accepted | Replace “creator distillation/copying” with abstract feature learning and an originality firewall; stories from magazines or creators are not rewrite inputs. | K9/T11, copyright research | Written authorization or verified public-domain status permits a specific use. |
| DEC-016 | Accepted | Evaluate natural female voices and Chinese-English mixing separately; first local candidates are Qwen3-TTS 0.6B Serena/Vivian, with VoxCPM2 as an 8GB-edge experiment and formal Qwen3/CosyVoice cloud APIs as budget-controlled backup. | K10, voice research, user voice feedback | Blind, stability, timestamp, rights, or cost evidence changes the ranking. |
