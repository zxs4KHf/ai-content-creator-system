# Current State

- Last verified: 2026-07-29
- Branch: `review/last-librarian-g1-g2`, tracking `origin/review/last-librarian-g1-g2`
- Implementation commit: `f9b56c2` (`feat: advance story comic and timing workflows`); this handoff context commit follows it
- Integration branch: local and remote `main` remain unchanged at `b898bd9`
- Worktree target after handoff commit: clean; ignored local environments, FFmpeg, dry-run plans, QA frames, voice samples, concat files, and preview videos remain local
- Current phase: the first original Bilibili pilot still waits at human G3/login; a verified per-shot comic hierarchy C shadow now joins A/B, strict cloud timing evidence remains listening-only, and six original classic-short-fiction candidates wait at G1

## Working

- [VERIFIED] `py -3 92_工具箱/verify_workflows.py` is the repeatable offline repository check. It parses and exercises all nine production CLIs, runs build/matrix/three TTS self-tests plus ten timing-contract unit tests, and validates the first story's real 26-cue subtitle manifest, 11-shot timeline, motion plan, and full/per-shot-comic filter contracts. It does not read keys, use the network, call paid APIs, or rewrite production media.
- [VERIFIED] The unchanged full-frame G3 candidate A remains `02_制作中/2026-07-26_故事线_最后一位图书管理员/素材/video/preview_v2.mp4`; the uniform comic shadow B remains `preview_comic_v2.mp4`. Neither was replaced.
- [VERIFIED] New shadow C is `素材/video/preview_comic_v3_hierarchy.mp4`: 72.28 seconds, 1080×1920, 25fps, H.264 High/AAC, SHA-256 `BDB8601558DC9A78C4D8404381F4E156646C290826F92A1BAAA5CA2DAC83BB15`. It fully decodes, and decoded audio MD5 `d275c38ba2e89618eb413de6209c078b` is identical to A/B.
- [VERIFIED] C uses `素材/comic_layout_plan.json`: 8 full context frames, 2 detail/evidence layouts (`shot_03b`, `shot_09`) that retain a complete context panel plus an explicit bounded focus panel, and 1 impact/endpoint layout (`shot_06`). Opening, both detail-shot starts/ends, impact, and strict ending were visually checked; subtitles and the persistent `AI生成内容` label remain readable.
- [VERIFIED] `build_video.py --comic-layout-plan` validates named shots, normalized focus geometry, complete bounded fields, even FFmpeg geometry, impact budgets, and `action_state/keyframe_role`. Omitting the plan preserves the prior comic output. Existing stills record `shot_04 initial/setup → shot_05 development/bridge → shot_06 final/endpoint`, with `shot_10 static/hold`; they do not claim generated I2V motion.
- [VERIFIED] K11/T13 now formalize endpoint-first motion: lock the final pose, spatial relationships, evidence, and camera endpoint; then derive initial/development/final, continuous middle frames, a complete FPV route, deceleration, and hold. Failed continuity falls back to static/context/evidence/hold or restrained Ken Burns.
- [VERIFIED] Six original classic-short-fiction G1 candidates are documented in `93_运行记录/推进_经典故事感G1候选_2026-07-29.md` and registered as GS01–GS06. Recommended first is GS02 `饭馆里永远没人坐的“第零桌”`; it has not passed G1, and no script or production folder was created.
- [DOCUMENTED] "Classic Story Club feel" means ordinary characters, one anomalous action, clear causality, visible reversal evidence, and an action-based aftertaste. Story Club and other modern published stories are not rewrite inputs. Ancient/folk routes remain research-only until source text, edition, modern arrangement, and audiovisual rights are separately verified.
- [VERIFIED] `tts_minimax.py` and `tts_dashscope.py` now have strict canonical word validators: complete result, integer milliseconds, valid/monotonic/non-overlapping intervals, optional audio bound, and normalized full-text coverage are all required. Undocumented provider aliases are never guessed.
- [VERIFIED] MiniMax recognizes only the documented `subtitle_file` as evidence, removes its expiring URL from persisted metadata, and still emits no publish `words[]`. DashScope normalizes documented result-generated/sentence envelopes offline but does not map undocumented word-item fields. Both mark real nonstreaming candidates `forced_alignment_required`; Qwen-Audio 3.0 Plus is explicitly treated as not supporting word timestamps.
- [VERIFIED] Fresh T10 dry-runs remained `planned_not_synthesized`: 374 billing characters, MiniMax HD estimate 0.1309 CNY and Qwen-Audio Plus estimate 0.05236 CNY, with forced alignment and no API call.

## Broken, blocked, or uncertain

- [DOCUMENTED] Human G3 is still required. A is full-frame, B is uniform comic framing, and C is per-shot hierarchy. Their narration is the same old AI-toned voice, so visual review must ignore shared voice quality. C is a shadow and does not replace A.
- [VERIFIED] The user's reported narration problem remains unsolved: no high-quality natural female candidate has been generated or ranked by ear. No cloud account/key/Workspace, billable call, voice enrollment, or local model download was used.
- [UNKNOWN] MiniMax's downloaded subtitle item fields and DashScope's actual `sentence.words[]` item schema remain unverified. One authorized real response fixture plus current provider documentation is required before positive mapping; until then publishing requires forced alignment.
- [VERIFIED] C's focus rectangles are screen coordinates applied after the existing Ken Burns transform, not semantic object tracking. Both detail-shot endpoints passed current visual inspection, but new images/motion plans require renewed start/end and subtitle-occlusion QA.
- [DOCUMENTED] Action metadata and endpoint-first cards are planning/validation contracts only. The first story still has no generated middle frames or real FPV path; deterministic still-image fallback remains the verified output.
- [VERIFIED] Qwen3-TTS/VoxCPM/CosyVoice weights were not downloaded. The Agent did not stop or alter user-owned GPU processes. Local execution still requires the operator to free GPU capacity and authorize the model/environment download.
- [DOCUMENTED] Bilibili registration/login, phone, OTP, CAPTCHA, real-name information, upload, platform declarations, and final publication remain operator-only visible-browser steps. No credentials, cookies, upload, or publication were handled.
- [DOCUMENTED] The matrix still contains no published observations; no viral result, column winner, account split, or mass replication is authorized.

## Verification performed

- Ran the full offline `verify_workflows.py` suite successfully after all implementation and documentation changes.
- Ran `build_video.py --self-test`, `matrix_tracker.py --self-test`, all three TTS self-tests, and the ten-test timing-contract module through the unified runner.
- Rendered a no-motion C QA preview, inspected full/detail/impact/ending frames, then rendered the full-motion `preview_comic_v3_hierarchy.mp4` without overwriting A/B.
- Fully decoded C with FFmpeg 8.1; verified 72.28s, 1080×1920, 25fps, H.264 High/AAC, SHA-256, and audio identity with A/B.
- Inspected C at opening, both ends of both detail shots, impact, and final hold. The focus evidence remains in-frame under the current Ken Burns plan; subtitles and AI label are readable.
- Rechecked `git diff --check`, staged-diff checks, credential/private-key patterns, portable-path leakage, and dry-run plans.
- Did not call real APIs, use provider keys/Workspace, pay, create/clone a voice, download model weights, stop GPU processes, register/login/upload/publish, approve G1/G3, or merge `main`.

## Next three actions

1. Human G1: approve one original classic-short-fiction candidate. Recommended command is `GS02 G1通过`; alternatives are GS01–GS06. Only after approval create its production folder and stop again at G2 with script, six-frame grayscale causality board, and comic layout draft.
2. Human G3 when convenient: compare A=`preview_v2.mp4`, B=`preview_comic_v2.mp4`, and C=`preview_comic_v3_hierarchy.mp4` for visual comprehension/fatigue while ignoring their identical old narration; choose one or return specific visual notes.
3. Authorize exactly one voice experiment when ready: MiniMax or DashScope under a stated ≤1 CNY cap with local Key/Workspace setup, or local Qwen after GPU release and model/environment authorization. Any result stays a shadow and still requires real timing/forced-alignment validation.

## Resume from here

The exact next productive action requires a human gate. If the operator says `GS02 G1通过`, start from `93_运行记录/推进_经典故事感G1候选_2026-07-29.md`, create one `02_制作中/` content folder from T1/T2/T13, produce the original G2 script and six-frame causality board, and stop for G2. For visual review, open `02_制作中/2026-07-26_故事线_最后一位图书管理员/04_评审单.md` and the A/B/C local videos. For voice work, read K10/T9/T12 and the matching guarded adapter; do not execute without the operator's explicit route, credentials/environment, and budget/download authorization.
