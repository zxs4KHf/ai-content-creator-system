# Project Context

- Last verified: 2026-07-29
- Verified repository baseline before the current research/workflow handoff: `1c5a296` on `review/last-librarian-g1-g2`; current work adds public creator evidence, voice-training/licensing routes, and a versioned character-animation asset contract
- Scope: AI-assisted self-media topic research, controlled column experiments, original story/knowledge production, storyboard and motion design, image/voice generation, video assembly, publishing preparation, and data review
- Known external gaps: authenticated Bilibili upload/publishing, human G3/G1 choices, real paid TTS response contracts, and local large-model execution remain unverified

## Purpose

[DOCUMENTED] This repository is an operating system for an AI-assisted Chinese self-media account. AI performs research and production work while the human operator controls G1 topic selection, G2 script approval, G3 final-media approval, and a separate irreversible publish confirmation. The durable workflow and operator commands are defined in `README.md`; positioning and content boundaries are defined in `00_账号定位/账号定位.md`.

The first production target is the original story `最后一位图书管理员`, stored under `02_制作中/`. It has one unchanged full-frame G3 candidate and one same-content comic-explainer shadow candidate.

## Architecture

The system has four durable layers:

- Evidence: `00_账号定位/` defines account positioning, content lines, audience, red lines, and reusable character assets.
- Constraints: `91_知识库/` contains hook, platform, narrative, diagnostic, visual-consistency, compliance, topic-radar, motion, matrix/originality, voice-routing, original comic-explainer, and stable character-animation/asset rules.
- Capabilities: `.claude/skills/` contains seven `zimeiti-*` production workflows plus three project-context workflows. `90_模板库/T14_角色动画样片实验卡.md` and `91_知识库/K12_稳定角色动画与资产管线.md` now connect versioned character/rig/age/outfit/face/right records to script, asset, and video production. `92_工具箱/` contains nine production CLIs (`align_subtitles.py`, `build_video.py`, `gen_images.py`, `make_jy_draft.py`, `matrix_tracker.py`, `tts_batch.py`, `tts_minimax.py`, `tts_dashscope.py`, and `tts_qwen_local.py`) plus `verify_workflows.py` as the repository-level offline check and a dedicated TTS timing-contract test module.
- Flow state: a content directory moves as a unit through `01_想法库/` → `02_制作中/` → `03_待发布/` → `04_已发布/`.

[VERIFIED] All nine production Python tools parse and expose CLI help. `verify_workflows.py` now runs their help paths, five self-test/test commands, and the first story's real subtitle, 11-shot timeline, motion, and full/per-shot-comic contracts without network or billable calls. Portable ffmpeg/ffprobe 8.1 rendered and fully decoded the full-frame candidate and both comic shadow generations, including the new per-shot hierarchy C version.

## Durable invariants

- G1, G2, and G3 require explicit human approval; publishing requires an additional explicit confirmation.
- State is represented by the content folder's location; move the whole folder instead of adding a competing status flag.
- `90_模板库/` defines repeatable process templates and `91_知识库/` defines generation constraints.
- A recurring character must have approved reference art and stable identity/style locks before batch scene generation.
- Logged-in publishing and private platform-data access run only on the local Windows machine; cloud agents must not receive platform cookies.
- AI-generated content must be declared on every platform, and publish candidates carry a persistent visible `AI生成内容` label.
- Facts must not be invented. Uncertain claims remain marked for verification and must be verified or removed before publishing.
- External creator material produces abstract, testable hypotheses only; no downloaded copy, transcript rewrite, recognizable causal chain, frame, music, voice, or branding enters generation.
- `故事会`、`意林`、网文和漫画 may inform audience promise or abstract grammar, but their stories are not rewrite inputs without verified permission.
- Account-matrix decisions require repeated within-platform evidence; one viral item never authorizes account splitting or mass duplication.
- Random video/TTS upgrades are shadow candidates: deterministic video and approved audio remain intact until the replacement passes explicit QA and G3. Comic hierarchy uses explicit full/detail/impact roles, bounded focus and impact budgets; action-state metadata cannot substitute for generated/validated intermediate motion.
- Stable recurring-character animation is a versioned asset system, not a prompt-only claim. Character, rig, age, outfit, face, and rights records are mandatory; body/face/lips/camera/contact/secondary tracks remain separate; stochastic video is capped at reversible hero shots. External game-derivative creators provide abstract production grammar only.
- Original stories with a classic short-fiction feel are the current content priority. Story Club and other modern publications remain grammar/audience references only; ancient or folk material needs a four-layer source/edition/modern-arrangement/audiovisual rights record before G1.
- External TTS is dry-run first, uses environment-only credentials, current non-understated pricing, a finite cost cap, media preflight, no-clobber output, resumable sidecars, and clone-consent records. Provider timestamp capability is not considered integrated until a real response contract passes.
- Local Qwen TTS execution accepts only a complete local 1.7B CustomVoice safetensors inventory with bundled tokenizer, architecture/content fingerprint, offline hub settings, `local_files_only`, dependency/GPU/VRAM/ffmpeg preflight, and explicit execution confirmation.
- Untimed captions longer than the 2×12-character display contract fail closed and require forced alignment. Character-weighted splitting is preview/diagnostic-only.

## Development entry points

- Read `AGENTS.md`, then `.context/CURRENT.md`, before material work.
- Install declared Python dependencies in an isolated environment with `92_工具箱/requirements.txt`; guarded dry-runs do not import optional cloud/local runtimes.
- Start with `py -3 92_工具箱/verify_workflows.py`; it parses and exercises all nine production CLIs, the video/matrix/TTS self-tests, timing-contract unit tests, and the first-story deterministic contracts.
- Keep narrow individual commands available when debugging, but rerun the repository-level check before handoff.
- Put portable `ffmpeg`/`ffprobe` on PATH before media rendering or any paid/local TTS execution.
- Prefer `gen_images.py --dry-run`, TTS default dry-runs, and `build_video.py --print-only` before API calls or media writes.
- Real paid/cloud calls, multi-GB model downloads, account actions, publishing, G1/G3 choices, and merging to `main` remain explicit operator gates.
