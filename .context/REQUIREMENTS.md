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
| REQ-013 | Implemented | [VERIFIED] | Plan shots by semantic beats and `F0/K/F1`, separate subject/environment/camera motion, keep a deterministic baseline, limit hero shots, validate real endpoint binding, and use fixed fallback/QA rules. | K8, T2/T8, `build_video.py`, first story motion plan |
| REQ-014 | Implemented | [VERIFIED] | Treat account/column growth as controlled experiments with one changed variable, per-platform observation windows, minimum sample coverage, rolling medians, safety stops, and no cross-platform universal score. | K9, T7, `matrix_tracker.py`, matrix experiment pool |
| REQ-015 | Accepted | [DOCUMENTED] | Learn only abstract functions from external creators; do not download or copy scripts, characters, causal chains, frames, music, voices, branding, or use published stories as rewrite material. | K9/T11, user direction, copyright/platform research |
| REQ-016 | Implemented | [VERIFIED] | Evaluate narration on separate naturalness and Chinese-English mixing gates, preserve a reproducible audio/timestamp manifest, require voice rights, and shadow-test new engines without overwriting approved audio. | K10, T9/T10, four local female Edge baselines |
| REQ-017 | Candidate | [DOCUMENTED] | Run a local Qwen3-TTS 1.7B `Serena/Vivian` PoC on the 8GB GPU (fall back to 0.6B only after measured OOM), then compare it with formally authorized MiniMax Speech 2.8 and low-cost Qwen3-TTS/CosyVoice cloud paths under hard budget controls. | Voice research, K10, `tts_minimax.py` |
| REQ-018 | Implemented | [VERIFIED] | Keep external TTS calls dry-run by default; read keys only from environment variables; require execution/billing confirmation, a finite cost cap, fresh non-understated pricing, ffmpeg preflight, no-clobber output, and resumable segment sidecars; preserve only sanitized provider metadata. Cloned voices additionally require an authorization record. | `tts_minimax.py` guard and resume contract tests |
| REQ-019 | Implemented | [VERIFIED] | Support a deterministic comic-explainer shadow cut for original/licensed stories while preserving narration, timeline, motion, subtitles, AI labeling, and the full-frame baseline; external comics and videos provide abstract grammar only, not story, frames, dialogue, or voice. | K11, T13, `build_video.py --frame-style comic`, rendered first-story shadow candidate |
| REQ-020 | Implemented | [VERIFIED] | Keep local large-model TTS offline-only at execution time: accept existing local official 1.7B CustomVoice safetensors and bundled tokenizer only, verify architecture/content inventory, disable hub downloads and pass `local_files_only`, preflight dependencies/GPU/free VRAM/ffmpeg, require explicit local-run confirmation, refuse silent overwrite, and safely resume matching partial segments. | `tts_qwen_local.py` self-test, preflight, dry-run, and guard tests |
| REQ-021 | Implemented | [VERIFIED] | Fail closed when a TTS manifest lacks word timestamps and a cue exceeds the 2×12-character display contract; require real word timing or forced alignment for publish subtitles, and keep character-weighted splitting preview/diagnostic-only. | `align_subtitles.py` manifest validation and long-cue rejection test |

Allowed statuses: `Implemented`, `Accepted`, `Candidate`, `Deferred`, `Rejected`, `Unknown`.
