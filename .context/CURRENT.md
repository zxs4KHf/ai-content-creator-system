# Current State

- Last verified: 2026-07-28
- Branch: `review/last-librarian-g1-g2`, tracking `origin/review/last-librarian-g1-g2`
- HEAD before current commit: `9cb8c92`
- Worktree: expected production changes are present; `main` remains at `b898bd9`; local environments, tools, backups, and intermediate previews are ignored
- Current phase: G1/G2 approved; G3 candidate, B 站 cover, and upload copy are ready; account login and human G3/publish confirmation remain

## Working

- [VERIFIED] C001 林伯 and C002 女孩/年轻管理员 character cards and selected reference sheets exist and were used for production.
- [VERIFIED] The story uses 11 source images: the original 10 shots plus `shot_03b.png` splitting the long third narration segment.
- [VERIFIED] `build_video.py --timeline` validates and consumes an explicit per-image timeline; `--motion-plan` applies deterministic movement with a settled end frame.
- [VERIFIED] Edge TTS produced a 72.27-second narration manifest; word timestamps produced 26 complete subtitle cues without truncating `1274` or English tokens.
- [VERIFIED] `align_subtitles.py --ai-label` produces a persistent top-right `AI生成内容` label in ASS output.
- [VERIFIED] `素材/video/preview_v2.mp4` is 72.28 seconds, 1080×1920, 25fps, H.264 High/AAC; full decode succeeds; loudness is about -14.6 LUFS with -1.5 dBFS true peak.
- [VERIFIED] The 11-frame QA montage shows all scenes, readable subtitles, stable character identity, and an unobtrusive AI label.
- [VERIFIED] B 站 cover `素材/bili/cover_1146x717.png` and short-pilot title, description, tags, and pinned comment are ready.

## Broken, blocked, or uncertain

- [VERIFIED] B 站 SMS login/registration requires the operator to enter phone, OTP, and any CAPTCHA directly in the visible local browser.
- [DOCUMENTED] G3 approval and a separate final publish confirmation are still required; no upload or publication has occurred.
- [DOCUMENTED] Preview intentionally has no BGM/SFX because no suitably licensed source was selected for the first workflow run.
- [UNKNOWN] B 站 upload category, creator declaration UI, and any account/real-name onboarding requirements must be observed after login.
- [DOCUMENTED] Several platform limits in `91_知识库/K2_平台规格手册.md` remain marked for manual verification.

## Verification performed

- Parsed all five Python tools and exercised their CLI help paths; the Jianying help text was made GBK-safe.
- Ran the video command in print-only mode and validated the 11 contiguous timeline slots.
- Rendered and fully decoded the final candidate with bundled ffmpeg 8.1; checked codec, resolution, frame rate, duration, pixel format, audio, and loudness.
- Generated and visually inspected exact shot-montage QA and the B 站 cover.
- Ran `git diff --check`; no whitespace errors were found.
- Did not publish, move the story to `03_待发布`, merge into `main`, or expose account credentials/cookies.

## Next three actions

1. Operator completes B 站 SMS login in the visible browser and reviews `素材/video/preview_v2.mp4` for G3.
2. After explicit G3 approval, create `05_发布物料.md`, move the story to `03_待发布`, and upload the video/cover while stopping before the final publish button.
3. After separate publish confirmation, publish, move the story to `04_已发布`, record the URL/time, and start the 48-hour review loop.

## Resume from here

Open `02_制作中/2026-07-26_故事线_最后一位图书管理员/04_评审单.md`, confirm the B 站 login state, and request G3 only after the operator has watched `素材/video/preview_v2.mp4`.
