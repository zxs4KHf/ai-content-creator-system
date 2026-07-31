# Current State

- Last verified: 2026-07-31
- Branch: `review/last-librarian-g1-g2`, tracking `origin/review/last-librarian-g1-g2`
- Implementation commit: `da358eb` (`feat: prepare GS02 G2 and local Qwen voice lab`)
- Latest documentation handoff: `2a87916` (`docs: clean contribution template whitespace`); Draft PR #1 targets `main` and awaits maintainer review.
- Integration branch: local and remote `main` remain unchanged at `b898bd9`
- Worktree target after this handoff commit: clean; model weights, Python environments, voice plans, setup manifest and any future WAV files remain ignored local state
- Current phase: GS02 has passed human G1 and now waits at human G2; local Qwen3-TTS is fully prepared but waits at the 7000 MiB free-VRAM gate; the first original pilot still waits at G3/login. The GitHub repository is publicly accessible at `https://github.com/zxs4KHf/ai-content-creator-system`.

## Working

- [VERIFIED] GS02 `《饭馆里永远没人坐的“第零桌”》` now has a complete G2 package under `02_制作中/2026-07-29_故事线_饭馆里永远没人坐的第零桌/`: topic contract, story text, 10-shot storyboard, six-frame grayscale causality board, G2 review form, motion design and comic layout plan.
- [VERIFIED] GitHub repository `zxs4KHf/ai-content-creator-system` is public; its default branch remains `main`, and this review branch remains independently pushed. No merge or rewrite was performed.
- [VERIFIED] Public contribution intake is now documented in root `CONTRIBUTING.md`: contributors work only from personal Forks and independent branches, submit one-topic Draft PRs, and may contribute reproducible issues, refined/de-identified experiment cases, documentation, tests or minimal fixes. `.github/` supplies Draft-PR, bug/try-run and experiment-report templates; `docs/外部试跑Agent约束提示词.md` gives external Agents a bounded, human-reviewed operating prompt.
- [VERIFIED] The story uses the frozen chain `异常账目 → 空间排除 → 怀疑免单/抹账 → 错单证据 → 老板复现错误 → 重做并落名`. Its reverse is evidence-backed rather than introduced at the ending.
- [VERIFIED] The recommended opening is A / K1 B4: `账上有“第零桌”，店里却没有。` B remains a visual-impact shadow option; C spends the final action too early.
- [VERIFIED] The visual contract is 10 shots with `7 full / 2 detail / 1 impact`, two reversible hero-motion candidates, 11 byte-identical style locks, a continuity ledger and zero formal image/audio/video files. A cross-shot pencil/identity conflict was removed by separating the clerk's fixed brass-pin marker from the shared cashier pencil.
- [VERIFIED] GS02 is original fictional production planning. It does not use Story Club, Yilin, web-fiction, comics, film or creator videos as a rewrite source; it carries `虚构故事 / 剧情演绎 / AI生成内容` and explicitly states that the responsibility column is not wage deduction or employee punishment.
- [VERIFIED] The official `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` snapshot is complete in an ignored local directory at commit `0c0e3051f131929182e2c023b9537f8b1c68adfe`. The two safetensors total 4,515,695,644 bytes and pass architecture, bundled-tokenizer and content-fingerprint checks.
- [VERIFIED] The isolated runtime uses Python 3.11.7, `qwen-tts 0.1.1`, `torch 2.11.0+cu130`, `torchaudio 2.11.0+cu130` and `soundfile 0.14.0`; CUDA sees the RTX 3060 Ti. `pip check` reports no broken requirements.
- [VERIFIED] Serena and Vivian share one fixed T10 warm-story probe, instruction and seed `42029`. Both dry-run plans are reproducible and report only the free-VRAM gate as not ready. Local details and hashes are in ignored `.tools/voice_lab/setup_manifest.json`; the durable sanitized record is `93_运行记录/推进_本地Qwen声音实验准备_2026-07-30.md`.
- [VERIFIED] `tts_qwen_local.py` now rejects CPU-only torch before model load, records/detects the official source revision, refuses source-revision mismatch, records runtime versions and WAV hashes, and verifies partial-audio hashes before resuming.
- [VERIFIED] The prior A/B/C visual candidates for the first story remain unchanged. No existing narration, image, video, account state or GPU process was changed.

## Broken, blocked, or uncertain

- [DOCUMENTED] GS02 must stop at human G2. No formal image, narration, subtitle timeline, animatic or video may be generated until the operator approves the story and selects A/B/C.
- [VERIFIED] The RTX 3060 Ti had only about 5.6 GiB free during the final checks; the local executor requires 7000 MiB. Two confirmed execution attempts stopped before model load. No audio was generated.
- [UNKNOWN] Qwen3-TTS 1.7B peak VRAM, RTF, stability and the actual Serena/Vivian listening quality on this machine remain unverified. Do not claim either voice is good until WAVs exist and pass T9 blind review.
- [DOCUMENTED] Do not lower the VRAM guard, kill unrelated GPU processes, use swap tricks or pre-emptively downgrade to 0.6B. Only consider 0.6B after a released-GPU, single-model, batch-1 1.7B run still fails/OOMs.
- [DOCUMENTED] The first story still needs human G3 visual choice among A/B/C; their narration remains the same old AI-toned baseline.
- [DOCUMENTED] Bilibili login/registration, phone/OTP/CAPTCHA, real-name information, upload, AI declarations and final publication remain operator-only visible-browser steps.
- [UNKNOWN] GS02's grayscale causality board has not been shown to an uninformed human. The responsibility-column interpretation and opening preference remain G2 judgments, not verified audience results.

## Verification performed

- Reconciled `CURRENT.md`, `PROJECT.md`, branch, HEAD, remote tracking, `main`, worktree and recent history before implementation; no starting contradiction was found.
- Checked every reachable Git commit for common GitHub/AWS/private-key secret signatures without printing candidate values, and checked tracked paths for environment, private-key, model and virtual-environment files; no matches were found before changing repository visibility to public. GitHub CLI then verified public visibility.
- Ran `py -3 92_工具箱/verify_workflows.py` after adding the public contribution intake documentation and templates; all offline checks passed. No GitHub branch-protection setting was changed automatically; the contributor guide records the recommended maintainer-side protections.
- Ran `py -3 92_工具箱/verify_workflows.py`: all nine CLI AST/help paths, six self-test/test commands, 10 TTS timing-contract tests, 26 real subtitle cues, and both full/comic 11-shot contracts passed offline.
- Loaded the GS02 comic plan through the real `build_video.py` validator: 10 shots and the `7/2/1` panel-role budget passed.
- Checked GS02 for identical style locks, prompt pronouns, stale pencil identity, formal media, JSON validity, secret patterns, machine absolute paths and whitespace errors; all passed.
- Verified official model revision metadata, both safetensors hashes, architecture and bundled tokenizer; verified CUDA availability and matching torch/torchaudio versions.
- Ran Serena/Vivian dry-runs and two guarded execution attempts. Both refused before model load because free VRAM was below 7000 MiB.
- Did not run real inference, generate/review audio, generate images/video, approve G2/G3, stop GPU processes, log in, upload, publish, merge `main`, or commit ignored model/environment/audio assets.

## Next three actions

1. Human G2: review `04_评审单.md`. Recommended response: `GS02 G2通过，钩子A`. If returning changes, name the hook, causality or responsibility-column concern.
2. When `nvidia-smi` reports at least 7000 MiB free, run Serena and Vivian one at a time from the fixed ignored plans. Preserve separate outputs and record WAV hash, peak VRAM, RTF and any error; then create a T9 blind-review card.
3. When convenient, complete the first story's G3 A/B/C visual review while ignoring their shared old narration.

## Resume from here

First run `nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits`. If free VRAM is below 7000 MiB, do not load Qwen or alter other processes; remain at the two human/VRAM gates. If it is at least 7000 MiB, read `93_运行记录/推进_本地Qwen声音实验准备_2026-07-30.md` and the ignored `.tools/voice_lab/setup_manifest.json`, then execute exactly one speaker with the fixed T10 probe, instruction, seed and source revision. For GS02, do not proceed past `04_评审单.md` until the operator explicitly approves G2 and chooses A/B/C.
