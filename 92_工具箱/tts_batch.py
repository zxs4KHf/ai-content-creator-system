#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量中文配音 (edge-tts) + 词级时间戳

为什么用 edge-tts 而不是本地开源 TTS:
  它自带**词级时间戳**(本地开源方案普遍不给), 字幕对齐白送。
  这是选它的主要理由, 免费只是附带好处。

三个必须知道的限制:
  1. 不支持多情感 style —— 中文音色元数据里没有 StyleList 字段,
     情绪只能靠 rate/pitch 和分段实现
  2. SSML 已被移除 —— <break> 不可用, 停顿靠"分段合成 + 插静音"(本脚本已实现)
  3. 有 403 速率限制 —— 已设并发 2 + 间隔 1.5s, 不要调高

依赖:
    pip install -U edge-tts
    # 拼接完整旁白需要 ffmpeg (系统已有即可)

用法:
    # 从分镜脚本自动抽口播文案
    python tts_batch.py --script ../02_制作中/xxx/02_分镜脚本.md --out ../02_制作中/xxx/素材/audio/

    # 从纯文本(一行一段)
    python tts_batch.py --text-file narration.txt --out out/ --voice zh-CN-YunxiNeural

    # 指定情绪预设
    python tts_batch.py --script ... --out ... --preset 悬疑

    # 列出所有中文音色
    python tts_batch.py --list-voices
"""

import argparse
import asyncio
import json
import re
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------- 音色

# 微软官方用 Novel 标签标注了适合朗读故事的中文音色
VOICES = {
    "zh-CN-YunxiNeural":      "男 · Novel/Lively        · 故事线首选",
    "zh-CN-XiaoxiaoNeural":   "女 · News,Novel/Warm     · 通用旁白",
    "zh-CN-YunjianNeural":    "男 · Sports,Novel/Passion· 悬疑/转折",
    "zh-CN-XiaoyiNeural":     "女 · Cartoon,Novel/Lively· 年轻俏皮",
    "zh-CN-YunxiaNeural":     "男 · Cartoon,Novel/Cute  · 少年感",
    "zh-CN-YunyangNeural":    "男 · News (无 Novel)     · 播音腔,不推荐做故事",
    "zh-CN-liaoning-XiaobeiNeural": "女 · 东北方言/Humorous · 市井/搞笑",
    "zh-CN-shaanxi-XiaoniNeural":   "女 · 陕西方言/Bright   · 地域题材",
}

# 情绪预设 (rate, pitch)
PRESETS = {
    "平静": ("-10%", "-2Hz"),
    "悬疑": ("-15%", "-5Hz"),
    "温柔": ("-8%",  "+0Hz"),
    "反转": ("+0%",  "+2Hz"),
    "明快": ("+5%",  "+3Hz"),
}

CONCURRENCY = 2      # ⚠️ 不要调高, edge-tts 有 403 速率限制
GAP_SECONDS = 1.5    # 每条之间的间隔


# ---------------------------------------------------------------- 文案抽取

def extract_from_script(md_path):
    """从 02_分镜脚本.md 抽取每镜的口播文案。

    优先从分镜表的"口播文案"列取; 取不到则退回"## 口播全文"段落按句切分。
    返回 [(段名, 文案), ...]
    """
    text = Path(md_path).read_text(encoding="utf-8")
    segs = []

    lines = text.splitlines()
    header_idx = col = shot_col = None
    for i, line in enumerate(lines):
        if "|" not in line or "口播" not in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        for j, c in enumerate(cells):
            if "口播" in c:
                col = j
            if "镜号" in c or c in ("镜", "#"):
                shot_col = j
        if col is not None:
            header_idx = i
            break

    if header_idx is not None:
        for line in lines[header_idx + 1:]:
            s = line.strip()
            if not s.startswith("|"):
                if segs:
                    break
                continue
            if re.fullmatch(r"\|[\s\-:|]+\|", s):
                continue
            cells = [c.strip() for c in s.strip("|").split("|")]
            if col >= len(cells):
                continue
            line_text = cells[col]
            if not line_text or line_text in ("-", "—", "（无）", "(无)"):
                continue
            num = len(segs) + 1
            if shot_col is not None and shot_col < len(cells):
                m = re.search(r"\d+", cells[shot_col])
                if m:
                    num = int(m.group())
            segs.append((f"{num:02d}", line_text))

    if not segs:
        m = re.search(r"##\s*口播全文\s*\n+(.*?)(?=\n##\s|\Z)", text, re.S)
        if m:
            body = re.sub(r"[（(].*?[)）]", "", m.group(1))
            for i, sent in enumerate(split_sentences(body), 1):
                segs.append((f"{i:02d}", sent))

    if not segs:
        sys.exit(f"没能从 {md_path} 抽出口播文案。\n"
                 f"请确认分镜表里有'口播文案'列, 或有 ## 口播全文 段落。")
    return segs


def split_sentences(text):
    """按中文标点切句"""
    text = re.sub(r"\s+", "", text)
    parts = re.split(r"(?<=[。！？…；])", text)
    return [p for p in (s.strip() for s in parts) if p]


def load_text_file(path):
    lines = [l.strip() for l in Path(path).read_text(encoding="utf-8").splitlines()]
    return [(f"{i:02d}", l) for i, l in enumerate([l for l in lines if l], 1)]


# ---------------------------------------------------------------- 合成

async def synth_one(seg_name, text, voice, rate, pitch, volume, out_dir, sem):
    import edge_tts
    async with sem:
        comm = edge_tts.Communicate(
            text, voice, rate=rate, volume=volume, pitch=pitch,
            boundary="WordBoundary",     # ⚠️ 默认是 SentenceBoundary, 要词级必须显式传
        )
        submaker = edge_tts.SubMaker()
        words = []
        mp3 = out_dir / f"{seg_name}.mp3"
        with open(mp3, "wb") as f:
            async for chunk in comm.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                    submaker.feed(chunk)
                    words.append({
                        "text": chunk["text"],
                        # offset 的单位是 100ns tick
                        "start_ms": chunk["offset"] / 10_000,
                        "end_ms": (chunk["offset"] + chunk["duration"]) / 10_000,
                    })
        (out_dir / f"{seg_name}.srt").write_text(submaker.get_srt(), encoding="utf-8")
        dur = words[-1]["end_ms"] / 1000 if words else 0.0
        print(f"  [OK] {seg_name}  {dur:6.2f}s  {len(words):3d} 个时间戳  {voice}")
        await asyncio.sleep(GAP_SECONDS)
        return {"name": seg_name, "text": text, "file": mp3.name,
                "duration_s": dur, "voice": voice, "words": words}


async def run(segs, voice, rate, pitch, volume, out_dir):
    sem = asyncio.Semaphore(CONCURRENCY)
    tasks = [synth_one(n, t, voice, rate, pitch, volume, out_dir, sem) for n, t in segs]
    return await asyncio.gather(*tasks)


# ---------------------------------------------------------------- 拼接

def make_silence(path, seconds):
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
         "-i", f"anullsrc=r=24000:cl=mono", "-t", str(seconds), "-q:a", "9", str(path)],
        check=True,
    )


def concat(results, out_dir, pause_ms, out_name="narration.mp3"):
    """把分段拼成完整旁白, 段间插静音。同步产出各段在总时间轴上的起止。"""
    sil = out_dir / f"_silence_{pause_ms}ms.mp3"
    if pause_ms > 0 and not sil.exists():
        make_silence(sil, pause_ms / 1000.0)

    listfile = out_dir / "_concat.txt"
    lines, timeline, cursor = [], [], 0.0
    for i, r in enumerate(results):
        if r is None:
            continue
        lines.append(f"file '{r['file']}'")
        timeline.append({"name": r["name"], "text": r["text"],
                         "start_s": round(cursor, 3),
                         "end_s": round(cursor + r["duration_s"], 3)})
        cursor += r["duration_s"]
        if pause_ms > 0 and i < len(results) - 1:
            lines.append(f"file '{sil.name}'")
            cursor += pause_ms / 1000.0
    listfile.write_text("\n".join(lines) + "\n", encoding="utf-8")

    out = out_dir / out_name
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
         "-i", str(listfile), "-c", "copy", str(out)],
        check=True, cwd=str(out_dir),
    )
    return out, timeline, cursor


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="批量中文配音 (edge-tts) + 词级时间戳")
    ap.add_argument("--script", help="02_分镜脚本.md 路径")
    ap.add_argument("--text-file", help="纯文本, 一行一段")
    ap.add_argument("--out", help="输出目录")
    ap.add_argument("--voice", default="zh-CN-YunxiNeural")
    ap.add_argument("--preset", choices=list(PRESETS), default="平静")
    ap.add_argument("--rate", help="覆盖预设, 如 -10%%  (负值必须用等号: --rate=-10%%)")
    ap.add_argument("--pitch", help="覆盖预设, 如 -2Hz")
    ap.add_argument("--volume", default="+0%")
    ap.add_argument("--pause-ms", type=int, default=400, help="段间静音毫秒")
    ap.add_argument("--list-voices", action="store_true")
    args = ap.parse_args()

    if args.list_voices:
        print("推荐的中文音色 (Novel 标签 = 微软官方标注适合朗读故事):\n")
        for v, d in VOICES.items():
            print(f"  {v:34s} {d}")
        print("\n完整列表: edge-tts --list-voices")
        return

    if not args.out:
        sys.exit("需要 --out")
    if not (args.script or args.text_file):
        sys.exit("需要 --script 或 --text-file")

    segs = extract_from_script(args.script) if args.script else load_text_file(args.text_file)
    rate, pitch = PRESETS[args.preset]
    rate = args.rate or rate
    pitch = args.pitch or pitch

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"共 {len(segs)} 段  音色={args.voice}  预设={args.preset} (rate={rate} pitch={pitch})")
    print(f"并发={CONCURRENCY} 间隔={GAP_SECONDS}s  (edge-tts 有 403 限流, 请勿调高)\n")

    results = asyncio.run(run(segs, args.voice, rate, pitch, args.volume, out_dir))
    results = [r for r in results if r]

    out, timeline, total = concat(results, out_dir, args.pause_ms)

    manifest = {
        "voice": args.voice, "rate": rate, "pitch": pitch,
        "pause_ms": args.pause_ms,
        "narration": out.name,
        "total_duration_s": round(total, 3),
        "segments": timeline,
        "raw": results,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n完整旁白: {out}  总时长 {total:.2f}s")
    print(f"清单: {out_dir/'manifest.json'}  (下一步 align_subtitles.py 会读它)")


if __name__ == "__main__":
    main()
