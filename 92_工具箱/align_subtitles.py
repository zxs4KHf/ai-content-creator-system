#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字幕时间轴生成

我们有口播原文, **不需要 ASR 识别, 只需要对齐**。三条路径, 按优先级:

  1. manifest  —— 直接用 edge-tts 的词级时间戳。最准, 白送, 首选。
  2. align     —— stable-ts 强制对齐。配音不是 edge-tts 生成时用。
  3. split     —— 按字数加权机械切分。兜底, 同时可作为前两者的 sanity check
                  (与 manifest 结果差异 >2s 说明对齐炸了)。

输出同时给 .srt 和 .ass。**推荐用 .ass**: ffmpeg 的 subtitles 滤镜处理 SRT 时
会用 PlayResX:384/PlayResY:288 的坐标系, MarginV 直接写 380 字幕会完全消失。

用法:
    # 首选: 用 edge-tts 的 manifest
    python align_subtitles.py --manifest ../02_制作中/xxx/素材/audio/manifest.json \
        --out ../02_制作中/xxx/素材/narration

    # 配音来自别处时
    python align_subtitles.py --align --audio narration.mp3 --text-file lines.txt --out narration

    # 兜底机械切分
    python align_subtitles.py --split --audio narration.mp3 --text-file lines.txt --out narration
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

MAX_CHARS_PER_LINE = 12      # 竖版每行 ≤12 字
MAX_LINES = 2
CJK = re.compile(r"[一-鿿㐀-䶿]")

# 标点的额外停顿权重(秒)
PAUSE = {"，": .20, "、": .15, "；": .25, "：": .20, "。": .40,
         "！": .40, "？": .40, "…": .45, "—": .30}

ASS_HEADER = """[Script Info]
Title: Vertical Short Video CN Subtitle
ScriptType: v4.00+
WrapStyle: 2
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Noto Sans CJK SC,104,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,1,0,1,5,3,2,80,80,{marginv},1
Style: AI_Label,Noto Sans CJK SC,36,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,3,1,0,9,40,40,52,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


# ---------------------------------------------------------------- 时间格式

def srt_time(sec):
    ms = int(round(max(sec, 0.0) * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def ass_time(sec):
    cs = int(round(max(sec, 0.0) * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


# ---------------------------------------------------------------- 断行

def wrap(text):
    """按 ≤12 字/行、≤2 行断行。优先在标点处断, 断不开再硬切。

    ⚠️ WrapStyle:2 表示不自动换行、只认 \\N ——
       所以每行字数必须在这里保证, libass 不会帮你。
    """
    text = text.strip()
    if len(text) <= MAX_CHARS_PER_LINE:
        return text

    # 找最靠近中点的标点
    mid = len(text) // 2
    best, best_dist = None, 1e9
    for i, ch in enumerate(text):
        if ch in "，,。.!！?？;；、…—" and 0 < i < len(text) - 1:
            d = abs(i - mid)
            if d < best_dist:
                best, best_dist = i, d
    if best is not None and max(best + 1, len(text) - best - 1) <= MAX_CHARS_PER_LINE:
        return text[:best + 1] + r"\N" + text[best + 1:]

    # 不在连续 ASCII 数字/单词中间硬切（例如 1274、OpenAI）。
    cut = min(MAX_CHARS_PER_LINE, len(text))
    if cut < len(text):
        while (cut > 1 and text[cut - 1].isascii() and text[cut - 1].isalnum()
               and text[cut].isascii() and text[cut].isalnum()):
            cut -= 1
        if cut < MAX_CHARS_PER_LINE // 2:
            cut = MAX_CHARS_PER_LINE
            while (cut < len(text) and text[cut - 1].isascii() and text[cut - 1].isalnum()
                   and text[cut].isascii() and text[cut].isalnum()):
                cut += 1
    lines = [text[:cut], text[cut:]] if cut < len(text) else [text]
    if len(lines) > MAX_LINES:
        print(f"  ⚠️ 过长, 已截断为 {MAX_LINES} 行: {text}", file=sys.stderr)
        lines = lines[:MAX_LINES]
    return r"\N".join(lines)


def strip_punct_tail(text):
    """字幕结尾的句号可以去掉, 视觉更干净"""
    text = text.replace('"', "").replace("“", "").replace("”", "")
    return re.sub(r"[。，、；,.;]$", "", text.strip())


# ---------------------------------------------------------------- 三条路径

def from_manifest(path):
    """路径 1: 用 edge-tts 的词级时间戳。最准。"""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    raw_by_name = {str(item["name"]): item for item in data.get("raw", [])}
    cues = []
    for seg in data["segments"]:
        raw = raw_by_name.get(str(seg["name"]))
        words = raw.get("words", []) if raw else []
        if not words:
            cues.append((seg["start_s"], seg["end_s"], seg["text"]))
            continue

        # 把原文中位于相邻词之间的标点附回前一个词。
        enriched = []
        original = seg["text"]
        cursor = 0
        for i, word in enumerate(words):
            token = word["text"].strip()
            at = original.find(token, cursor)
            if at < 0:
                display = token
            else:
                end = at + len(token)
                if i + 1 < len(words):
                    next_token = words[i + 1]["text"].strip()
                    next_at = original.find(next_token, end)
                    suffix = original[end:next_at] if next_at >= 0 else ""
                else:
                    suffix = original[end:]
                display = re.sub(r"\s+", "", token + suffix)
                cursor = end
            enriched.append({**word, "display": display})

        # 以 2 行 × 12 字为硬上限；标点或明显停顿处优先结束当前字幕块。
        chunks, current = [], []
        for i, word in enumerate(enriched):
            proposed = "".join(w["display"] for w in current + [word])
            if current and len(proposed.replace(" ", "")) > MAX_CHARS_PER_LINE * MAX_LINES:
                chunks.append(current)
                current = []
            current.append(word)

            next_gap = 0
            if i + 1 < len(enriched):
                next_gap = enriched[i + 1]["start_ms"] - word["end_ms"]
            current_text = "".join(w["display"] for w in current).strip()
            if (re.search(r"[，,。.!！？?；;…]$", current_text) or next_gap >= 350) and len(current_text) >= 6:
                chunks.append(current)
                current = []
        if current:
            chunks.append(current)

        for i, chunk in enumerate(chunks):
            start = seg["start_s"] + chunk[0]["start_ms"] / 1000
            if i + 1 < len(chunks):
                end = seg["start_s"] + max(
                    chunk[-1]["end_ms"], chunks[i + 1][0]["start_ms"] - 50
                ) / 1000
            else:
                end = seg["end_s"]
            end = min(seg["end_s"], max(end, start + 0.4))
            text = "".join(w["display"] for w in chunk).strip()
            cues.append((start, end, text))
    return cues, data.get("total_duration_s")


def from_align(audio, sentences):
    """路径 2: stable-ts 强制对齐"""
    try:
        import stable_whisper
    except ImportError:
        sys.exit("需要: pip install 'stable-ts==2.19.1' openai-whisper\n"
                 "(stable-ts 已于 2026-05 归档, 功能可用但不再修复, 请锁版本)")
    model = stable_whisper.load_model("medium")
    result = model.align(
        str(audio), "\n".join(sentences), language="zh",
        original_split=True,     # 保留输入换行作为分句边界
        regroup=False,           # 不关会覆盖 original_split
        suppress_silence=True, fast_mode=False, vad=False, max_word_dur=3.0,
    )
    cues = [(s.start, s.end, s.text.strip()) for s in result.segments]
    if len(cues) != len(sentences):
        print(f"  ⚠️ 对齐输出 {len(cues)} 条 ≠ 输入 {len(sentences)} 行, 请人工核对",
              file=sys.stderr)
    return cues, cues[-1][1] if cues else 0.0


def from_split(audio, sentences, lead_in=0.3, tail=0.3):
    """路径 3: 按字数加权机械切分。TTS 语速恒定时误差通常可接受。"""
    total = probe_duration(audio)

    def weight(ch):
        if CJK.match(ch):
            return 1.0
        if ch.isdigit():
            return 1.0
        if ch.isalpha():
            return 0.45
        return 0.0

    costs = [(sum(weight(c) for c in s), sum(PAUSE.get(c, 0.0) for c in s))
             for s in sentences]
    tw = sum(w for w, _ in costs)
    tp = sum(p for _, p in costs)
    budget = total - lead_in - tail - tp
    if budget <= 0:
        budget = total - lead_in - tail
        costs = [(w, 0.0) for w, _ in costs]
    spw = budget / tw if tw else 0.0

    cues, t = [], lead_in
    for s, (w, p) in zip(sentences, costs):
        d = max(w * spw + p, 0.5)
        cues.append((t, t + d, s))
        t += d
    return cues, total


def probe_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    return float(out)


# ---------------------------------------------------------------- 写盘

def write_srt(cues, path):
    lines = []
    for i, (st, en, tx) in enumerate(cues, 1):
        body = strip_punct_tail(tx)
        body = wrap(body).replace(r"\N", "\n")
        lines.append(f"{i}\n{srt_time(st)} --> {srt_time(en)}\n{body}\n")
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def write_ass(cues, path, marginv=380, ai_label=False, total=None):
    body = [ASS_HEADER.format(marginv=marginv)]
    if ai_label:
        if not total:
            raise ValueError("写入 AI 标识需要有效的总时长")
        body.append(
            f"Dialogue: 1,0:00:00.00,{ass_time(total)},AI_Label,,0,0,0,,AI生成内容"
        )
    for st, en, tx in cues:
        text = wrap(strip_punct_tail(tx))
        body.append(f"Dialogue: 0,{ass_time(st)},{ass_time(en)},Default,,0,0,0,,{text}")
    Path(path).write_text("\n".join(body) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="字幕时间轴生成")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--manifest", help="[首选] tts_batch.py 产出的 manifest.json")
    src.add_argument("--align", action="store_true", help="stable-ts 强制对齐")
    src.add_argument("--split", action="store_true", help="按字数机械切分(兜底)")
    ap.add_argument("--audio", help="音频路径 (align/split 需要)")
    ap.add_argument("--text-file", help="口播文本, 一行一段 (align/split 需要)")
    ap.add_argument("--out", required=True, help="输出前缀, 会生成 .srt 和 .ass")
    ap.add_argument("--marginv", type=int, default=380,
                    help="底部留白: 380=三平台通投 / 300=抖音+小红书 / 260=只发小红书")
    ap.add_argument("--check", action="store_true",
                    help="同时跑机械切分做 sanity check, 差异 >2s 会告警")
    ap.add_argument("--ai-label", action="store_true",
                    help="在 ASS 顶部持续显示‘AI生成内容’，发布成片建议固定开启")
    args = ap.parse_args()

    if args.manifest:
        cues, total = from_manifest(args.manifest)
        src_name = "manifest (edge-tts 词级时间戳)"
    else:
        if not (args.audio and args.text_file):
            sys.exit("--align / --split 需要 --audio 和 --text-file")
        sentences = [l.strip() for l in
                     Path(args.text_file).read_text(encoding="utf-8").splitlines() if l.strip()]
        if args.align:
            cues, total = from_align(args.audio, sentences)
            src_name = "stable-ts 强制对齐"
        else:
            cues, total = from_split(args.audio, sentences)
            src_name = "机械切分"

    out = Path(args.out)
    srt_path = out.with_suffix(".srt")
    ass_path = out.with_suffix(".ass")
    write_srt(cues, srt_path)
    write_ass(cues, ass_path, args.marginv, args.ai_label, total)

    print(f"来源: {src_name}")
    print(f"条数: {len(cues)}   总时长: {total:.2f}s" if total else f"条数: {len(cues)}")
    print(f"  {srt_path}")
    print(f"  {ass_path}   (MarginV={args.marginv})")
    print("\n[注意] 合成时请用 .ass —— ffmpeg 处理 SRT 会用 384x288 坐标系, MarginV 会失效")

    if args.check and args.manifest and args.audio and args.text_file:
        sentences = [c[2] for c in cues]
        ref, _ = from_split(args.audio, sentences)
        worst = max(abs(a[0] - b[0]) for a, b in zip(cues, ref))
        flag = "[注意] 对齐可能有问题" if worst > 2.0 else "OK"
        print(f"\nsanity check: 与机械切分的最大起点差异 {worst:.2f}s  [{flag}]")


if __name__ == "__main__":
    main()
