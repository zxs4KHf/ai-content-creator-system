# Current State

- Last verified: 2026-07-28
- Branch: `review/last-librarian-g1-g2`, tracking `origin/review/last-librarian-g1-g2`
- Workflow implementation commit: `fff2a0b`; this handoff context commit follows it
- Integration branch: local and remote `main` remain unchanged at `b898bd9`
- Worktree: implementation commit is clean; ignored local environments, tools, G3 preview, concat files, and female voice A/B samples remain local
- Current phase: first B 站 pilot is still at human G3/login; workflow v2.1 for motion, creator-feature learning, matrix experiments, and natural female/bilingual voice evaluation is implemented

## Working

- [VERIFIED] The existing `素材/video/preview_v2.mp4` remains the G3 candidate: 72.28 seconds, 1080×1920, 25fps, H.264 High/AAC, with persistent `AI生成内容`; SHA-256 remained `F3145AB63BCF7E37B9D843B2E05D77A1CA08386BE4DD12DF23BFADB1C9BD80E4` after the workflow changes.
- [VERIFIED] K8/T8 now require semantic beats, `F0 → optional K → F1`, separate subject/environment/camera channels, at most one strong channel, a deterministic full-film baseline, 2–3 hero shots, real endpoint-binding labels, fixed fallback, and five-point/contact-frame QA.
- [VERIFIED] `build_video.py` consumes old motion-plan v1 and new v2. The first story v2 plan preserves the existing Ken Burns parameters, marks shots 4/6/10 as hero candidates, and dry-runs all 11 contiguous timeline slots without re-rendering or changing G3 media.
- [VERIFIED] K9/T7/T11, `外部样本特征池.md`, and `矩阵实验池.md` distinguish `pilot / discovery / controlled`; external creator work produces one abstract hypothesis only and is never a rewrite/download source.
- [VERIFIED] `matrix_tracker.py` validates the experiment CSV, explicit safety state, observation windows, one changed-variable contract, sample coverage, account/series confounds, and per-platform medians; it deliberately emits no cross-platform score.
- [VERIFIED] K10/T9/T10 define a rights-aware voice manifest and separate gates for naturalness and Chinese-English mixing. Local priority is Qwen3-TTS 0.6B `Serena/Vivian`; VoxCPM2 is an 8GB-edge experiment; formal Qwen3/CosyVoice APIs are budget-controlled cloud backup.
- [VERIFIED] Four ignored Edge female baselines were generated and fully decoded from the same three-part test text: Xiaoxiao 47.604s, Xiaoyi 47.388s, Ava Multilingual 47.124s, and Emma Multilingual 54.180s. They did not overwrite the 72.27-second pilot narration.
- [VERIFIED] The repo now has seven `zimeiti-*` workflows and six Python CLIs; `zimeiti-matrix` was initialized and validated with the skill-creator tooling.

## Broken, blocked, or uncertain

- [VERIFIED] B 站 SMS login/registration still requires the operator to enter phone, OTP, CAPTCHA, and any real-name data directly in the visible local browser. No credentials, cookies, upload, or publication were handled.
- [DOCUMENTED] Human G3 approval and a separate final publish confirmation are still required. After G3, the publishing file is now `06_发布物料.md` because `05_运动设计.md` is part of G2→G3.
- [UNKNOWN] The four Edge samples have not received a human blind-listening score; mechanical generation, timestamps, duration, and decode passed, but “best voice” is subjective.
- [DOCUMENTED] Qwen3-TTS/VoxCPM weights were not downloaded. A Qwen3-TTS 0.6B PoC is the next local test, but the multi-GB download and separate environment require operator approval after checking free disk space.
- [DOCUMENTED] No cloud TTS account, API key, free quota, or paid call was used. A formal cloud A/B requires the operator to create/approve the account, set the key locally, enable budget controls, and accept the provider terms.
- [DOCUMENTED] The matrix contains no published observations yet; discovery/controlled conclusions cannot be claimed before coverage exists.
- [DOCUMENTED] Preview still has no BGM/SFX because no suitably licensed source was selected. Several K2 platform limits and live B 站 category/declaration/onboarding UI remain unverified.

## Verification performed

- Parsed all six Python tools without bytecode and exercised every `--help` path.
- Ran `matrix_tracker.py --self-test`, validated the header-only production CSV in Markdown/JSON, and checked that missing safety state fails the contract.
- Validated production JSON, motion-plan v1 compatibility, v2 hero budget/levels, and the 11-slot `build_video.py --print-only` command.
- Validated `.claude/skills/zimeiti-matrix` with `quick_validate.py`.
- Generated and fully decoded all four female voice baseline MP3s; retained their manifests and word boundaries locally under ignored `素材/audio/voice_ab/`.
- Rechecked the G3 preview hash, `git diff --check`, remote drift (`0/0` before commit), and that `main`/`origin/main` remain at `b898bd9`.
- Did not subjectively rank voices, download local TTS weights, call paid APIs, rerender the G3 candidate, log in, upload, publish, move the story, or merge into `main`.

## Next three actions

1. Operator watches `素材/video/preview_v2.mp4`, listens to the four local `素材/audio/voice_ab/*/narration.mp3` samples, then returns `G3 通过/返工` and optional voice preferences. SMS login may be completed in the visible browser at the same time.
2. After explicit G3 approval, create `06_发布物料.md`, move the story to `03_待发布`, upload video/cover, and stop before the final publish button; publish only after the separate confirmation.
3. With explicit approval for a multi-GB local-model download, check free disk, isolate the environment, and run Qwen3-TTS 0.6B `Serena/Vivian` on `90_模板库/T10_语音盲测基准.txt`; otherwise wait for a formally configured low-cost cloud key/budget. In parallel, the next content cycle can start only after G1 selects O01/F02/C01 from `矩阵实验池.md`.

## Resume from here

Start with `02_制作中/2026-07-26_故事线_最后一位图书管理员/04_评审单.md` and the unchanged G3 preview. For voice review, open the four `narration.mp3` files listed in `93_运行记录/女声与中英混读候选_2026-07-28.md`. Do not download model weights or call a cloud API until the operator chooses the local or cloud path and authorizes its resource/account side effects.
