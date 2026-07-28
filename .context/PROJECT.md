# Project Context

- Last verified: 2026-07-28
- Verified against commit: `1fa1ab6` (recovered v2 baseline)
- Scope: AI-assisted self-media topic research, controlled account/column experiments, script and storyboard production, asset generation, video assembly, publishing preparation, and data review
- Known gaps: B 站 authenticated upload/publishing and several live platform limits remain unverified; local Qwen3-TTS/VoxCPM and formal low-cost cloud TTS are researched but not yet installed or called

## Purpose

[DOCUMENTED] This repository is an operating system for an AI-assisted Chinese self-media account. AI performs research and production work while the human operator approves three gates: G1 topic selection, G2 script, and G3 final media. The durable workflow and operator commands are defined in `README.md`; positioning and content boundaries are defined in `00_账号定位/账号定位.md`.

The first production target is a story-line item named `最后一位图书管理员`, currently stored under `02_制作中/`.

## Architecture

The system has four durable layers:

- Evidence: `00_账号定位/` defines account positioning, content lines, audience, and red lines.
- Constraints: `91_知识库/` contains hook, platform, narrative, diagnostic, visual-consistency, compliance, topic-radar, motion, matrix/originality, and voice-routing rules that generation must follow.
- Capabilities: `.claude/skills/zimeiti-*` describes seven agent workflows; `92_工具箱/` contains Python CLIs for image generation, TTS, subtitle alignment, ffmpeg video assembly, Jianying draft generation, and matrix-data validation.
- Flow state: a content directory moves as a unit through `01_想法库/` → `02_制作中/` → `03_待发布/` → `04_已发布/`.

[VERIFIED] The six Python files under `92_工具箱/` parse successfully and expose CLI entry points. A repository-local virtual environment exercised `google-genai`, `edge-tts`, subtitle tooling, matrix self-tests, and motion-plan v1/v2 validation; portable `ffmpeg`/`ffprobe` 8.1 rendered and verified the first G3 candidate and four ignored female voice baselines.

## Durable invariants

- G1, G2, and G3 require explicit human approval; publishing requires an additional explicit confirmation.
- State is represented by the content folder's location; move the whole folder instead of adding a competing status flag.
- `90_模板库/` defines process templates and `91_知识库/` defines generation constraints.
- A recurring character must have approved reference art and stable identity/style locks before batch scene generation.
- Logged-in publishing and private platform-data access run only on the local Windows machine; cloud agents must not receive platform cookies.
- AI-generated content must be labeled on every platform.
- Published video candidates also carry a persistent visible `AI生成内容` label generated with the ASS subtitle track.
- Facts must not be invented. Uncertain facts remain marked for verification and must be verified or removed before publishing.
- Publishing material should adapt one core asset across platforms rather than independently rewriting each version.
- External creator material produces abstract hypotheses only; no downloaded copy, transcript rewrite, recognizable causal chain, frame, music, voice, or branding enters generation.
- Account-matrix decisions require repeated within-platform evidence; one viral item never authorizes account splitting or mass duplication.
- Random video/TTS upgrades are shadow candidates: deterministic video and approved audio remain intact until the replacement passes explicit QA and G3.

## Development entry points

- Read `AGENTS.md`, then `.context/CURRENT.md`, before material work.
- Install Python dependencies in an isolated environment with `92_工具箱/requirements.txt`.
- Run syntax checks without producing cache files, then run each of the six CLIs with `--help`.
- Install and verify `ffmpeg`/`ffprobe` before exercising `build_video.py` or media-duration checks.
- Prefer `gen_images.py --dry-run` and `build_video.py --print-only` before API calls or media writes.
- No general automated test suite currently exists; use `matrix_tracker.py --self-test`, motion-plan dry-runs, and narrow fixture-based smoke tests before production assets or publishing.
