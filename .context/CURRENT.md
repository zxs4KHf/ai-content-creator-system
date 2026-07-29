# Current State

- Last verified: 2026-07-29
- Branch: `review/last-librarian-g1-g2`, tracking `origin/review/last-librarian-g1-g2`
- Verified baseline before this worktree: `1c5a296` (`docs: hand off story comic and timing round`); the current research/workflow handoff commit follows it
- Integration branch: local and remote `main` remain unchanged at `b898bd9`
- Worktree target after handoff commit: clean; ignored local environments, FFmpeg, dry-run plans, QA frames, voice samples, concat files, and preview videos remain local
- Current phase: the first original Bilibili pilot still waits at human G3/login; six original classic-short-fiction candidates wait at G1; high-quality game-derivative public evidence, voice-training routes, and versioned character-animation methodology are now documented and wired into the workflow

## Working

- [VERIFIED] `py -3 92_工具箱/verify_workflows.py` remains the repeatable offline check. After the research/workflow changes it passed all nine production CLI AST/help paths, five self-test/test commands, 10 TTS timing-contract tests, 26 real subtitle cues, and both full/comic 11-shot contracts without network, credentials, billable calls, or production-media writes.
- [VERIFIED] Four new reports separate public evidence, technical inference, unknowns, licenses, 8GB feasibility, cost, and replication stability: `调研_高质量游戏二创公开证据_2026-07-29.md`, `调研_GitHub声音训练与变声路线_2026-07-29.md`, `调研_角色动画服饰年龄变化复刻路线_2026-07-29.md`, and `调研_高质量游戏二创稳定复刻总路线_2026-07-29.md`.
- [VERIFIED] The referenced Bilibili UID 59528875 is `喜欢长离捏`. Its public homepage exposes `blender`, `AE教程`, and `剪辑教程` favorite categories; the latest inspected representative video is marked `含AI生成内容` and credits a two-person `UP主 + 后期` team. A separate inspected video demonstrates a child/downsized character variant.
- [INFERRED] The public work is best explained by a reusable 3D asset/rig/animation/camera/render/post pipeline with AI assistance, not by ordinary prompt-only video generation. The exact software versions, asset sources, rig/mocap route, voice model, training recipe, and GitHub identity remain unverified.
- [VERIFIED] K12/T14 now define a durable character-animation contract: `CHARACTER_ID / ASSET_VERSION / AGE_VARIANT / OUTFIT_ID / FACE_SET / RIG_VERSION / RIGHTS_RECORD`, separate body/face/lips/camera/contact/secondary tracks, deterministic fallback, 1–3 generated hero shots, five-point/contact QA, resource budgets, and stop conditions.
- [VERIFIED] `zimeiti-script`, `zimeiti-visual`, and `zimeiti-video` now load K12/T14 when long-term characters, outfit/age variants, 2D/3D rigs, or stochastic hero shots are involved. The visual skill's stale Qwen recommendation was corrected from 0.6B-first to 1.7B-first with measured-OOM fallback.
- [DOCUMENTED] The stable reference-quality route is asset-driven. For this project, classic-story comic/2D remains the near-term default; an original Blender character pipeline starts only after content evidence, while random I2V/V2V remains a reversible hero-shot experiment.
- [VERIFIED] The voice audit routes MiniMax Voice Design + Speech 2.8 HD as the first cost-effective original-voice challenger: 9.9 CNY on first activation and 3.5 CNY/10k billing characters; the existing 374-billing-character T10 sample estimates 0.1309 CNY synthesis cost. Qwen3-TTS 1.7B and VoxCPM2 remain the two local candidates.
- [VERIFIED] VoxCPM2's official repository states approximately 8GB inference VRAM and 5–10 minutes for LoRA adaptation. This is a boundary, not a local stability guarantee; the machine had about 5.7GB free VRAM during the audit. F5 official Base weights and current Fish local weights remain excluded from monetized production by their non-commercial/research license paths.
- [VERIFIED] The unchanged visual candidates remain A=`preview_v2.mp4`, B=`preview_comic_v2.mp4`, and C=`preview_comic_v3_hierarchy.mp4`; no production media or existing audio was replaced.

## Broken, blocked, or uncertain

- [DOCUMENTED] Human G1 is still required before creating a classic-story production folder. Recommended first candidate remains GS02 `饭馆里永远没人坐的“第零桌”`.
- [DOCUMENTED] Human G3 is still required for A/B/C. Their narration is the same old AI-toned voice, so visual review must ignore shared voice quality.
- [VERIFIED] No high-quality natural female candidate was generated or ranked by ear. No cloud key/account, billable call, voice design/clone, model download, Blender project, motion-capture recording, or GPU process change was performed.
- [UNKNOWN] No public creator statement proves the exact Blender/UE/MMD, model extraction, rig, mocap, AE, TTS/VC, training, or GitHub route. Public favorite categories are evidence of interest, not proof of actual project files.
- [DOCUMENTED] The user's old QQ group history was not bulk-crawled. A minimal keyword list and redaction protocol are in the public-evidence report; private messages, member identities, and group files remain out of scope unless the operator supplies a narrow, sanitized export or explicitly authorizes a visible read-only check.
- [DOCUMENTED] Unauthorized game-character/voice cloning is not a production route. Research may compare GPT-SoVITS, RVC, Seed-VC, CosyVoice, IndexTTS2, OpenVoice, Qwen, and VoxCPM technically, but publishable assets require original/authorized voice data and separate IP/model/audio rights.
- [VERIFIED] Qwen3-TTS/VoxCPM/CosyVoice/FramePack/LTX weights were not downloaded. Model-code licenses do not automatically cover checkpoints, base models, adapters, inputs, or outputs.
- [DOCUMENTED] Bilibili registration/login, phone, OTP, CAPTCHA, real-name information, upload, platform declarations, and final publication remain operator-only visible-browser steps. No upload or publication was handled.

## Verification performed

- Restored and reconciled the branch/worktree against `CURRENT.md`, `PROJECT.md`, Git history, HEAD, remote tracking, and `main`; no contradiction was found.
- Committed and pushed the previous story-comic/timing handoff as `1c5a296`; `main` stayed at `b898bd9`.
- Read the referenced public Bilibili profile and two representative public video pages without downloading video/audio/transcripts; verified profile categories, public AI label, team credits, and visible asset characteristics.
- Cross-checked technical claims against primary GitHub repositories, official model cards/docs, MiniMax pricing, Alibaba voice-design documentation, UE documentation/EULA, Kuro's public derivative-creation guideline, and CAC deep-synthesis/AI-label rules.
- Ran `git diff --check`, placeholder/evidence/source scans, and the full offline `verify_workflows.py`; all passed.
- Did not use private group data, call APIs, pay, design/clone a real voice, download weights, stop GPU processes, create 2D/3D assets, approve G1/G3, log in/upload/publish, or merge `main`.

## Next three actions

1. Human G1: approve one original classic-short-fiction candidate. Recommended command: `GS02 G1通过`. Then create its production folder and stop again at G2 with script, six-frame grayscale causality board, comic layout, and K12 asset-tier/reuse fields.
2. Human G3 when convenient: compare A/B/C for visual comprehension and fatigue while ignoring their identical narration; choose one or return specific visual notes.
3. Authorize exactly one voice experiment: recommended MiniMax original Voice Design + Speech 2.8 HD under about 10.5 CNY total, or a single local Qwen3-TTS 1.7B/VoxCPM2 download after GPU release. No role/actor clone.

## Resume from here

The exact next production action requires a human gate. If the operator says `GS02 G1通过`, start from `93_运行记录/推进_经典故事感G1候选_2026-07-29.md`, create one `02_制作中/` folder from T1/T2/T13, add the K12 `REUSE_POTENTIAL / ASSET_TIER / HERO_MOTION` fields, produce the original G2 package, and stop for G2. For a voice experiment, start from K10/T9/T12 and `调研_GitHub声音训练与变声路线_2026-07-29.md`; require the chosen route, credentials/environment, budget/download authorization, and keep output as a shadow. For character animation, use K12/T14 and do a 20-second original-character sample before any full 3D episode.
