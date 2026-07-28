# Current State

- Last verified: 2026-07-29
- Branch: `review/last-librarian-g1-g2`, tracking `origin/review/last-librarian-g1-g2`
- Implementation commits: `0a9d17c` (guarded voice/comic workflows) and `df7cef8` (guarded DashScope adapter); this handoff context commit follows them
- Integration branch: local and remote `main` remain unchanged at `b898bd9`
- Worktree target after handoff commit: clean; ignored local environments, tools, test fixtures, voice samples, concat files, QA frames, and preview videos remain local
- Current phase: the first original Bilibili pilot is waiting at human G3/login; comic explanation and high-quality female-voice routes are implemented as shadow workflows, and the next original content candidates are waiting at G1

## Working

- [VERIFIED] The unchanged full-frame G3 candidate is `素材/video/preview_v2.mp4`: 72.28 seconds, 1080×1920, 25fps, H.264 High/AAC, persistent `AI生成内容`, SHA-256 `F3145AB63BCF7E37B9D843B2E05D77A1CA08386BE4DD12DF23BFADB1C9BD80E4`.
- [VERIFIED] The comic-explainer shadow candidate is `素材/video/preview_comic_v2.mp4`: the same original story, 11-shot timeline, narration, subtitles, motion, and AI label, with a non-cropping 9:16 white panel over a dark blurred background. It is 72.28 seconds, 1080×1920, 25fps, H.264 High/AAC; SHA-256 `2D3C8DED87BEF30A9BA85D38F6FEAA6BD5C58EFB65609055BC9CDBFA31EC2204`.
- [VERIFIED] Both visual candidates decode completely and their decoded audio MD5 is identical: `d275c38ba2e89618eb413de6209c078b`. The comic version does not replace the full-frame G3 candidate.
- [VERIFIED] K11/T13 define original comic explanation as causal state changes, full/detail/impact panel hierarchy, semantic cuts, restrained motion, non-leaking reversals, and sound punctuation. `故事会`、`意林`、web fiction, comics, and creator videos are grammar/audience references only, never rewrite or frame sources without rights.
- [VERIFIED] The repository now has nine Python CLIs. `build_video.py --frame-style comic` preserves the existing timeline/motion/subtitle contract; `align_subtitles.py` validates manifest order and word timing and rejects long untimed publish cues instead of overflowing or truncating them.
- [VERIFIED] `tts_minimax.py` supports `synthesize / voices / design / self-test`, defaults to dry-run, uses official China endpoints only, enforces current price floors and a 30-day snapshot, finite cost cap, ffmpeg preflight, no-clobber output, resumable paid sidecars, sanitized metadata, and cloned-voice authorization records.
- [VERIFIED] `tts_dashscope.py` covers Beijing `qwen-audio-3.0-tts-plus`, `cosyvoice-v3.5-plus`, and `cosyvoice-v3.5-flash` with dry-run, current-price, API/Workspace, SDK, budget, rights, no-clobber, media, and resume guards. The non-streaming first pass is listening-only and explicitly requires later forced alignment.
- [VERIFIED] `tts_qwen_local.py` accepts an existing local official Qwen3-TTS 1.7B CustomVoice directory only, requires root architecture plus bundled speech tokenizer and at least 4GB of safetensors, hashes the content inventory, forces offline/local-only loading, preflights dependencies/GPU/free VRAM/ffmpeg, and safely resumes matching partial segments.
- [VERIFIED] T12 and T9 define original female-voice design, semantic directing, Chinese/English blind gates, long-listening fatigue, stability, timestamp, rights, and cost review. MiniMax HD remains the reference-linked quality anchor; Qwen-Audio 3.0/CosyVoice 3.5 are lower-price formal challengers; local order is Qwen3-TTS 1.7B → VoxCPM2 → CosyVoice3.
- [VERIFIED] The next non-voice G1 recommendations are O01 `第七个来还伞的人`, F02 `同一句“吃了吗”，机器为什么翻了七次`, then renamed C01. No new story script or production folder was created before G1.
- [VERIFIED] K5 now distinguishes code, checkpoint, base model, dependency weights, output terms, input rights, and exact model IDs; it no longer incorrectly applies FaceID/InsightFace or one FLUX license to entire families.

## Broken, blocked, or uncertain

- [DOCUMENTED] Human G3 is still required. The operator must compare A=`preview_v2.mp4` and B=`preview_comic_v2.mp4` for visual comprehension/fatigue while ignoring their shared old narration, then choose A, B, or return both for revision.
- [VERIFIED] The existing narration still has the user's reported AI tone. No strong candidate has been generated: no cloud account/key/Workspace, billable call, voice enrollment, or model download was used.
- [UNKNOWN] MiniMax `Podcast_girl` must be queried from the operator's real account before use. MiniMax supports word subtitles, but its real returned field shape is not yet mapped into `words[]`; first paid output remains listening-only until that contract is validated.
- [UNKNOWN] DashScope model/voice IDs, SDK response, actual cost receipt, and streaming word events have not been tested with a real Beijing Workspace. CosyVoice 3.5 has no system voice and requires an original designed voice or an authorized clone.
- [VERIFIED] Qwen3-TTS/VoxCPM/CosyVoice weights were not downloaded. D: has about 123GB free, but the RTX 3060 Ti 8GB recently had only about 0.6GB free because user-owned GPU processes were running. The Agent did not stop or alter them. Local execution requires the operator to release GPU capacity and authorize the approximately 4.52GB Qwen model plus isolated environment.
- [DOCUMENTED] Bilibili login/registration requires the operator to enter phone, OTP, CAPTCHA, and any real-name data directly in the visible local browser. No credentials, cookies, upload, or publication were handled.
- [DOCUMENTED] Publishing still requires G3, creation of `06_发布物料.md`, folder movement to `03_待发布/`, authenticated upload, and a separate final publish confirmation.
- [DOCUMENTED] The matrix contains no published observations; no column winner, account split, or mass-replication claim is authorized. O01/F02/C01 are G1 candidates only.
- [DOCUMENTED] The pilot still has no BGM/SFX because no suitably licensed source was selected. Several live platform limits remain unverified.

## Verification performed

- Parsed all nine Python tools without bytecode and exercised every `--help` path.
- Ran `tts_minimax.py self-test`, `tts_dashscope.py self-test`, `tts_qwen_local.py self-test`, and `matrix_tracker.py --self-test`.
- Verified MiniMax, DashScope, and Qwen default dry-runs; correct 374-character/cost estimates; portable manifest paths; partial-sidecar reuse; mismatch refusal; no-clobber behavior; price-floor/NaN/cost-cap guards; missing ffmpeg; cloned-voice rights; official endpoint/Workspace/local-directory restrictions; and missing SDK/model preflight.
- Re-generated subtitles from the existing Edge word manifest. Confirmed a long no-word-time manifest fails closed and requests forced alignment.
- Dry-ran both `full` and `comic` video commands with all 11 contiguous slots and verified the comic filter uses a non-cropping 864×1536 panel.
- Rendered and fully decoded `preview_comic_v2.mp4`; checked media specs/hash, compared decoded audio MD5 with the full-frame candidate, and visually inspected 0/25/50/75% plus the strict ending frame.
- Rechecked `git diff --check`, staged-diff checks, secret-pattern scans, remote branch state, and that `main`/`origin/main` remain at `b898bd9`.
- Did not rank voices by ear, call paid APIs, register accounts, create cloud voices, download TTS weights, stop GPU processes, log in, upload, publish, move the story folder, approve G1/G3, or merge into `main`.

## Next three actions

1. Operator gives the key visual decision: `G3 A通过`, `G3 B通过`, or specific return notes after comparing `preview_v2.mp4` and `preview_comic_v2.mp4` without judging their shared narration.
2. Operator authorizes exactly one first voice experiment: (a) configure MiniMax and allow ≤1 CNY T10 A/B after querying `Podcast_girl`; (b) configure Beijing DashScope Key/Workspace plus an original CosyVoice voice and allow ≤1 CNY; or (c) release GPU and authorize the ~4.52GB Qwen 1.7B download/environment. New audio stays a shadow candidate.
3. Operator selects the next original content G1: O01, F02, or revised C01. Recommended order is O01 → F02 → C01; no source-story adaptation is allowed.

## Resume from here

Start at `02_制作中/2026-07-26_故事线_最后一位图书管理员/04_评审单.md`. If the operator chooses G3, preserve the unselected visual version and proceed only through publishing preparation. If the operator chooses a voice route, read K10/T9/T12 and the matching guarded adapter, perform the smallest T10 shadow A/B under the stated authorization, and validate real timestamp/cost fields before any production replacement. If the operator chooses G1, begin from `93_运行记录/推进_非语音G1候选_2026-07-28.md` and stop again at G2 after producing the selected original script and storyboard.
