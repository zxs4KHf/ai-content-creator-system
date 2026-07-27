# Project Context

- Last verified: 2026-07-27
- Verified against commit: `1fa1ab6` (recovered v2 baseline)
- Scope: AI-assisted self-media topic research, script and storyboard production, asset generation, video assembly, publishing preparation, and data review
- Known gaps: external generation services, ffmpeg video assembly, platform publishing integrations, and platform limits have not been verified on this Windows machine

## Purpose

[DOCUMENTED] This repository is an operating system for an AI-assisted Chinese self-media account. AI performs research and production work while the human operator approves three gates: G1 topic selection, G2 script, and G3 final media. The durable workflow and operator commands are defined in `README.md`; positioning and content boundaries are defined in `00_账号定位/账号定位.md`.

The first production target is a story-line item named `最后一位图书管理员`, currently stored under `02_制作中/`.

## Architecture

The system has four durable layers:

- Evidence: `00_账号定位/` defines account positioning, content lines, audience, and red lines.
- Constraints: `91_知识库/` contains hook, platform, narrative, diagnostic, visual-consistency, compliance, and topic-radar rules that generation must follow.
- Capabilities: `.claude/skills/zimeiti-*` describes six agent workflows; `92_工具箱/` contains Python CLIs for image generation, TTS, subtitle alignment, ffmpeg video assembly, and Jianying draft generation.
- Flow state: a content directory moves as a unit through `01_想法库/` → `02_制作中/` → `03_待发布/` → `04_已发布/`.

[VERIFIED] The five Python files under `92_工具箱/` parse successfully and expose CLI entry points. `requirements.txt` declares optional integrations such as `google-genai` and `edge-tts`; video assembly also requires external `ffmpeg` and `ffprobe` binaries.

## Durable invariants

- G1, G2, and G3 require explicit human approval; publishing requires an additional explicit confirmation.
- State is represented by the content folder's location; move the whole folder instead of adding a competing status flag.
- `90_模板库/` defines process templates and `91_知识库/` defines generation constraints.
- A recurring character must have approved reference art and stable identity/style locks before batch scene generation.
- Logged-in publishing and private platform-data access run only on the local Windows machine; cloud agents must not receive platform cookies.
- AI-generated content must be labeled on every platform.
- Facts must not be invented. Uncertain facts remain marked for verification and must be verified or removed before publishing.
- Publishing material should adapt one core asset across platforms rather than independently rewriting each version.

## Development entry points

- Read `AGENTS.md`, then `.context/CURRENT.md`, before material work.
- Install Python dependencies in an isolated environment with `92_工具箱/requirements.txt`.
- Run syntax checks without producing cache files, then run each CLI with `--help`.
- Install and verify `ffmpeg`/`ffprobe` before exercising `build_video.py` or media-duration checks.
- Prefer `gen_images.py --dry-run` and `build_video.py --print-only` before API calls or media writes.
- No automated test suite currently exists; use narrow fixture-based smoke tests before production assets or publishing.
